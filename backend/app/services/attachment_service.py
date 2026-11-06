"""
Attachment service: stream upload, SHA-256 (ALWAYS computed), StorageBackend delegation.
SHA-256 is stored unconditionally - forensic integrity guarantee.
"""
import hashlib
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attachment import Attachment
from app.services.storage.resolver import get_storage_backend

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

ALLOWED_MIME_PREFIXES = [
    "image/", "application/pdf", "text/", "application/json",
    "application/zip", "application/x-zip-compressed",
    "application/octet-stream",
    "application/vnd.ms-excel", "application/vnd.openxmlformats",
    "application/msword",
]

# Map detected MIME types to safe file extensions
_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "application/vnd.ms-excel": ".xls",
    "application/msword": ".doc",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/json": ".json",
}

# Text formats recognised by extension *and* content (#150). filetype only
# knows binary signatures, so without this every text file is stored as
# application/octet-stream and can't be previewed safely.
_TEXT_EXT_TO_MIME: dict[str, str] = {
    ".txt": "text/plain",
    ".log": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
}
_TEXT_SNIFF_BYTES = 8192

# Stored MIME types the evidence register may render as plain text.
TEXT_PREVIEW_MIMES = frozenset({"text/plain", "text/csv", "application/json"})
TEXT_PREVIEW_MAX_BYTES = 1024 * 1024


def _looks_like_text(data: bytes) -> bool:
    head = data[:_TEXT_SNIFF_BYTES]
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as exc:
        # A multi-byte character cut off at the sniff boundary is still text.
        return exc.start >= len(head) - 3 and len(data) > _TEXT_SNIFF_BYTES
    return True


def _get_actual_mime(data: bytes, filename: str | None = None) -> str:
    """Detect MIME type from actual file bytes (first 2048 bytes).

    Plain-text formats have no signature: they are recognised only when the
    extension is a known text one and the content really is UTF-8 text.
    """
    import filetype
    kind = filetype.guess(data[:2048])
    if kind:
        return kind.mime
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in _TEXT_EXT_TO_MIME and _looks_like_text(data):
        return _TEXT_EXT_TO_MIME[ext]
    return "application/octet-stream"


def _validate_mime(mime_type: str) -> None:
    allowed = any(mime_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{mime_type}' is not allowed",
        )


async def upload_attachment(
    db: AsyncSession,
    org_id: str,
    incident_id: str,
    file: UploadFile,
    timeline_entry_id: str | None = None,
    uploaded_by: str | None = None,
) -> Attachment:
    # Stream and compute SHA-256 simultaneously
    hasher = hashlib.sha256()
    chunks = []
    total_size = 0

    while chunk := await file.read(65536):  # 64KB chunks
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {MAX_FILE_SIZE // 1024 // 1024}MB limit",
            )
        hasher.update(chunk)
        chunks.append(chunk)

    data = b"".join(chunks)
    sha256 = hasher.hexdigest()

    # Detect MIME from actual file bytes - reject content-type spoofing
    actual_mime = _get_actual_mime(data, file.filename)
    _validate_mime(actual_mime)

    # Use a safe extension derived from detected MIME, not the original filename
    safe_ext = _MIME_TO_EXT.get(actual_mime, "")
    if not safe_ext and actual_mime.startswith("text/"):
        safe_ext = ".txt"

    # Store via backend - UUID-based path, outside web root
    file_uuid = str(uuid.uuid4())
    stored_path = f"attachments/{incident_id}/{file_uuid}{safe_ext}"

    backend = get_storage_backend()
    await backend.store(data, stored_path)

    attachment = Attachment(
        org_id=org_id,
        incident_id=incident_id,
        timeline_entry_id=timeline_entry_id,
        uploaded_by=uploaded_by,
        original_name=file.filename or "upload",
        stored_path=stored_path,
        mime_type=actual_mime,
        file_size=total_size,
        sha256=sha256,
        storage_backend=backend.backend_name,
        is_screenshot=actual_mime.startswith("image/"),
    )
    db.add(attachment)
    await db.flush()
    return attachment


async def get_attachment(db: AsyncSession, attachment_id: str, incident_id: str) -> Attachment:
    result = await db.execute(
        select(Attachment).where(
            Attachment.id == attachment_id, Attachment.incident_id == incident_id
        )
    )
    att = result.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return att


async def get_attachment_url(attachment: Attachment, expires_in: int = 3600) -> str:
    backend = get_storage_backend()
    return await backend.get_url(attachment.stored_path, expires_in)


async def get_text_preview(attachment: Attachment) -> tuple[str, bool]:
    """First TEXT_PREVIEW_MAX_BYTES of a text attachment, decoded as UTF-8.

    Only for the allowlisted stored MIME types, never from the file name.
    """
    if attachment.mime_type not in TEXT_PREVIEW_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Preview not available for this file type",
        )
    data = await get_storage_backend().retrieve(attachment.stored_path)
    truncated = len(data) > TEXT_PREVIEW_MAX_BYTES
    return data[:TEXT_PREVIEW_MAX_BYTES].decode("utf-8", errors="replace"), truncated


async def delete_attachment(db: AsyncSession, attachment: Attachment) -> None:
    backend = get_storage_backend()
    try:
        await backend.delete(attachment.stored_path)
    except FileNotFoundError:
        pass  # Already gone from storage - still remove DB record
    await db.delete(attachment)
    await db.flush()
