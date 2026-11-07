"""Backup tools (#149). Run inside the backend container::

    docker compose exec backend python -m app.cli.backup decrypt <file.enc> <out.tar.gz>
    docker compose exec backend python -m app.cli.backup rekey [--dry-run]
    docker compose exec backend python -m app.cli.backup verify [--incident <id>]

decrypt  Decrypt a backup file (current or legacy format) to its .tar.gz bundle.
rekey    Re-encrypt every local backup not yet using BACKUP_ENCRYPTION_KEY,
         and its cloud copy if it has one. Safe to rerun; the original is only
         replaced after the new file has been decrypted back and checked.
verify   Rehash every stored attachment and compare with the recorded SHA-256.
         Read-only. Exits 1 if any file is missing or doesn't match.
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import TextIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import backup_crypto

EXIT_OK = 0
EXIT_FAIL = 1


# ── decrypt ──────────────────────────────────────────────────────────────────

def decrypt_file(src: Path, dst: Path, out: TextIO = sys.stdout) -> int:
    try:
        plaintext = backup_crypto.decrypt(src.read_bytes())
    except FileNotFoundError:
        print(f"error: {src} not found", file=out)
        return EXIT_FAIL
    except backup_crypto.BackupKeyError as exc:
        print(f"error: {exc}", file=out)
        return EXIT_FAIL
    dst.write_bytes(plaintext)
    print(f"decrypted {src.name} -> {dst} ({len(plaintext)} bytes)", file=out)
    return EXIT_OK


# ── rekey ────────────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rekey_file(path: Path) -> bool:
    """Re-encrypt one file with the active key. Returns False if it was already current.

    The original is replaced only after the new file decrypts back to the
    same bytes. If anything fails the original is left untouched.
    """
    if not backup_crypto.needs_rekey(backup_crypto.read_header(path)):
        return False
    plaintext = backup_crypto.decrypt(path.read_bytes())  # raises on a bad tag
    expected = _sha256(plaintext)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(backup_crypto.encrypt(plaintext))
        if _sha256(backup_crypto.decrypt(tmp.read_bytes())) != expected:
            raise backup_crypto.BackupKeyError("re-encrypted file did not verify")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()

    sidecar = path.with_suffix(".json")
    if sidecar.exists():
        try:
            manifest = json.loads(sidecar.read_text())
        except ValueError:
            manifest = {}
        manifest["format_version"] = backup_crypto.FORMAT_V2
        manifest["key_fingerprint"] = backup_crypto.active_fingerprint()
        sidecar.write_text(json.dumps(manifest, indent=2))
    return True


async def rekey(db: AsyncSession, backup_dir: Path, dry_run: bool = False, out: TextIO = sys.stdout) -> int:
    from app.models.backup import BackupRecord
    from app.services import backup_service

    fp = backup_crypto.active_fingerprint()
    if backup_crypto.active_key_source() != backup_crypto.KEY_SOURCE_DEDICATED:
        print("warning: BACKUP_ENCRYPTION_KEY is not set; files would be re-encrypted with the "
              "SECRET_KEY-derived key. Set it first.", file=out)
        return EXIT_FAIL

    paths = sorted(p for p in backup_dir.glob("irdoc_backup_*.enc") if backup_service._FILENAME_RE.match(p.name))
    done = skipped = failed = 0
    for path in paths:
        try:
            if not backup_crypto.needs_rekey(backup_crypto.read_header(path)):
                skipped += 1
                continue
            if dry_run:
                print(f"would rekey {path.name}", file=out)
                done += 1
                continue
            rekey_file(path)
        except (OSError, backup_crypto.BackupKeyError) as exc:
            print(f"FAILED {path.name}: {exc}", file=out)
            failed += 1
            continue

        record = (await db.execute(
            select(BackupRecord).where(BackupRecord.filename == path.name)
        )).scalars().first()
        if record is not None:
            record.key_fingerprint = fp
            if record.destination != "local":
                try:
                    await backup_service.upload_remote_copy(db, record.destination, path)
                except Exception as exc:  # noqa: BLE001 - report and keep going
                    print(f"warning: {path.name} rekeyed locally, but the {record.destination} copy "
                          f"was not replaced: {exc}", file=out)
            await db.commit()
        print(f"rekeyed {path.name}", file=out)
        done += 1

    verb = "would rekey" if dry_run else "rekeyed"
    print(f"{verb} {done}, already current {skipped}, failed {failed} (key {fp})", file=out)
    return EXIT_FAIL if failed else EXIT_OK


# ── verify ───────────────────────────────────────────────────────────────────

async def verify(db: AsyncSession, incident_id: str | None = None, out: TextIO = sys.stdout) -> int:
    from app.models.attachment import Attachment
    from app.services.attachment_service import backend_for_attachment

    query = select(Attachment).order_by(Attachment.incident_id, Attachment.created_at)
    if incident_id:
        query = query.where(Attachment.incident_id == incident_id)
    attachments = list((await db.execute(query)).scalars().all())

    ok = mismatch = missing = 0
    backends: dict[str, object] = {}
    for att in attachments:
        label = f"{att.incident_id}/{att.id} {att.original_name}"
        try:
            name = att.storage_backend or "local"
            if name not in backends:
                backends[name] = await backend_for_attachment(db, att)
            data = await backends[name].retrieve(att.stored_path)
        except (FileNotFoundError, LookupError) as exc:
            print(f"MISSING  {label} ({exc})", file=out)
            missing += 1
            continue
        computed = _sha256(data)
        if computed == att.sha256.lower():
            print(f"OK       {label}", file=out)
            ok += 1
        else:
            print(f"MISMATCH {label} recorded={att.sha256} computed={computed}", file=out)
            mismatch += 1

    print(f"{ok} OK, {mismatch} mismatch, {missing} missing ({len(attachments)} files)", file=out)
    return EXIT_FAIL if mismatch or missing else EXIT_OK


# ── entry point ──────────────────────────────────────────────────────────────

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli.backup", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("decrypt", help="decrypt a backup file to .tar.gz")
    d.add_argument("src", type=Path)
    d.add_argument("dst", type=Path)
    r = sub.add_parser("rekey", help="re-encrypt local backups with BACKUP_ENCRYPTION_KEY")
    r.add_argument("--dry-run", action="store_true")
    v = sub.add_parser("verify", help="check stored attachments against their SHA-256")
    v.add_argument("--incident", help="only this incident id")
    return parser


async def _with_db(fn, *args):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        return await fn(db, *args)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "decrypt":
        return decrypt_file(args.src, args.dst)
    from app.services.backup_service import BACKUP_DIR
    if args.command == "rekey":
        return asyncio.run(_with_db(rekey, BACKUP_DIR, args.dry_run))
    return asyncio.run(_with_db(verify, args.incident))


if __name__ == "__main__":
    sys.exit(main())
