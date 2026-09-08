"""
Attachment service: stream upload, SHA-256 (ALWAYS computed), StorageBackend delegation.
SHA-256 is stored unconditionally — forensic integrity guarantee.
"""
import hashlib
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
}


def _get_actual_mime(data: bytes) -> str:
    """Detect MIME type from actual file bytes (first 2048 bytes)."""
    import filetype
    kind = filetype.guess(data[:2048])
    return kind.mime if kind else "application/octet-stream"


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

    # Detect MIME from actual file bytes — reject content-type spoofing
    actual_mime = _get_actual_mime(data)
    _validate_mime(actual_mime)

    # Use a safe extension derived from detected MIME, not the original filename
    safe_ext = _MIME_TO_EXT.get(actual_mime, "")
    if not safe_ext and actual_mime.startswith("text/"):
        safe_ext = ".txt"

    # Store via backend — UUID-based path, outside web root
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


async def delete_attachment(db: AsyncSession, attachment: Attachment) -> None:
    backend = get_storage_backend()
    try:
        await backend.delete(attachment.stored_path)
    except FileNotFoundError:
        pass  # Already gone from storage — still remove DB record
    await db.delete(attachment)
    await db.flush()
