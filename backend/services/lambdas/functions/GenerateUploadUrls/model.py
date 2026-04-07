from typing import Literal
from pydantic import BaseModel, field_validator


class FileManifestItem(BaseModel):
    name: str
    content_type: str
    type: Literal["invoice", "gadget_photo"]


class GenerateUploadUrlsRequest(BaseModel):
    files: list[FileManifestItem]

    @field_validator("files")
    @classmethod
    def validate_files(cls, files):
        invoices = [f for f in files if f.type == "invoice"]
        photos = [f for f in files if f.type == "gadget_photo"]

        if len(invoices) != 1:
            raise ValueError("Exactly one invoice file is required")
        if len(photos) < 1:
            raise ValueError("At least one gadget photo is required")
        if len(photos) > 5:
            raise ValueError("Maximum of five gadget photos allowed")
        for f in photos:
            if not f.content_type.startswith("image/"):
                raise ValueError("Gadget photos must be image files")
        for f in invoices:
            if not (
                f.content_type.startswith("image/")
                or f.content_type == "application/pdf"
            ):
                raise ValueError("Invoice must be a PDF or image file")
        return files


class PresignedUrlItem(BaseModel):
    file_key: str
    presigned_url: str
    type: str


class GenerateUploadUrlsResponse(BaseModel):
    upload_session_id: str
    scan_job_id: str
    urls: list[PresignedUrlItem]
