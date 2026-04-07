from __future__ import annotations

from pydantic import BaseModel


class GenerateSignatureUploadUrlResponse(BaseModel):
    presigned_url: str
    s3_key: str
    asset_id: str
