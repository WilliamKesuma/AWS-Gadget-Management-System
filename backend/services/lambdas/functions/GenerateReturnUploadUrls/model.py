from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class ReturnFileManifestItem(BaseModel):
    name: str
    type: Literal["photo", "admin-signature"]
    content_type: str = "image/jpeg"


class GenerateReturnUploadUrlsRequest(BaseModel):
    files: list[ReturnFileManifestItem]

    @field_validator("files")
    @classmethod
    def validate_files(
        cls, files: list[ReturnFileManifestItem]
    ) -> list[ReturnFileManifestItem]:
        photos = [f for f in files if f.type == "photo"]
        admin_sigs = [f for f in files if f.type == "admin-signature"]
        if len(photos) == 0 and len(admin_sigs) == 0:
            raise ValueError("At least one photo or admin signature file is required")
        if len(admin_sigs) > 1:
            raise ValueError("At most one admin signature file is allowed")
        return files


class ReturnPresignedUrlItem(BaseModel):
    file_key: str
    presigned_url: str
    type: str
    content_type: str


class GenerateReturnUploadUrlsResponse(BaseModel):
    upload_urls: list[ReturnPresignedUrlItem]
