from datetime import datetime
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class RecordCreate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class RecordUpdate(BaseModel):
    data: dict[str, Any] | None = None


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None


class Page(BaseModel, Generic[T]):
    total: int
    items: list[T]
    page: int
    page_size: int
    pages: int
