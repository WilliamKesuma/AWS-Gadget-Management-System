from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class IssueFileManifestItem(BaseModel):
    name: str
    type: Literal["photo"]
    content_type: str = "application/octet-stream"


class GenerateIssueUploadUrlsRequest(BaseModel):
    files: list[IssueFileManifestItem]

    @field_validator("files")
    @classmethod
    def validate_files(
        cls, files: list[IssueFileManifestItem]
    ) -> list[IssueFileManifestItem]:
        if len(files) < 1:
            raise ValueError("At least one issue photo file is required")
        return files


class IssuePresignedUrlItem(BaseModel):
    file_key: str
    presigned_url: str
    type: str
    content_type: str


class GenerateIssueUploadUrlsResponse(BaseModel):
    upload_urls: list[IssuePresignedUrlItem]
