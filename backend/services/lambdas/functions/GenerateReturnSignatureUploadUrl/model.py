from __future__ import annotations

from pydantic import BaseModel


class GenerateReturnSignatureUploadUrlRequest(BaseModel):
    file_name: str


class GenerateReturnSignatureUploadUrlResponse(BaseModel):
    presigned_url: str
    s3_key: str
    return_id: str
    asset_id: str
