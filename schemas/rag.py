from typing import Any

from pydantic import BaseModel, Field


class RagDocument(BaseModel):
    content: str = Field(..., min_length=1)
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagIngestRequest(BaseModel):
    documents: list[RagDocument] = Field(..., min_length=1)


class RagIngestResponse(BaseModel):
    inserted: int


class RagUploadFileResult(BaseModel):
    filename: str
    inserted: int = 0
    skipped: bool = False
    error: str | None = None


class RagUploadResponse(BaseModel):
    inserted: int
    files: list[RagUploadFileResult]


class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)


class RagSearchResult(BaseModel):
    id: int
    content: str
    source: str | None = None
    metadata: dict[str, Any]
    score: float | None = None


class RagSearchResponse(BaseModel):
    query: str
    results: list[RagSearchResult]
