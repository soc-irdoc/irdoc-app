"""Evidence register (#150): a read-only view of what an incident has collected."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

EvidenceKind = Literal["timeline", "incident"]
EvidenceSort = Literal[
    "name", "kind", "source", "type", "size", "sha256", "uploaded_by", "uploaded_at", "screenshot"
]


class EvidenceSource(BaseModel):
    """The timeline entry a file is attached to."""
    entry_id: UUID
    entry_type: str
    occurred_at: datetime
    excerpt: str


class EvidenceAssetChip(BaseModel):
    id: UUID
    name: str
    asset_type: str


class EvidenceIOCMatch(BaseModel):
    id: UUID
    ioc_type: str
    value: str


class EvidenceFileOut(BaseModel):
    id: UUID
    kind: EvidenceKind
    original_name: str
    mime_type: str | None
    file_size: int | None
    sha256: str
    is_screenshot: bool
    uploaded_by: UUID | None
    uploaded_by_name: str | None
    uploaded_at: datetime
    source: EvidenceSource | None
    # None (rather than []) when the user may not read assets / IOCs.
    assets: list[EvidenceAssetChip] | None = None
    ioc_matches: list[EvidenceIOCMatch] | None = None
    # IOCs linked to the file's timeline entry (#152)
    linked_iocs: list[EvidenceIOCMatch] | None = None


class EvidenceIOCOut(BaseModel):
    id: UUID
    ioc_type: str
    value: str
    tlp_level: str
    linked_entries: list[EvidenceSource]
    file_count: int
    # Attachments whose SHA-256 equals this IOC's value.
    matching_files: list[UUID]


class TextPreviewOut(BaseModel):
    text: str
    truncated: bool
