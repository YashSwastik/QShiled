"""
Shared Pydantic v2 schema utilities.
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    """Base for all response schemas — enables ORM mode."""
    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    """Standard error response body."""
    detail: str
    code: str | None = None


class PaginatedResponse(OrmBase):
    """Generic paginated list wrapper."""
    total: int
    page: int
    page_size: int
    items: list  # subclasses override with typed List[X]
