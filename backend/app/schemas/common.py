"""
Shared schema utilities and envelope types.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    page: int = 1
    per_page: int = 50
    total: int = 0


class Response(BaseModel, Generic[T]):
    data: T
    meta: Meta | None = None
    error: str | None = None


class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 50

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page
