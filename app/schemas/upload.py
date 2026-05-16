"""Schemas for upload API responses."""

from pydantic import BaseModel


class UploadedFileResponse(BaseModel):
    """Metadata for one uploaded PDF."""

    document_id: str
    filename: str


class UploadResponse(BaseModel):
    """Response returned after creating an upload batch."""

    batch_id: str
    uploaded_files: list[UploadedFileResponse]

