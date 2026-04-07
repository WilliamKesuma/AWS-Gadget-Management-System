from __future__ import annotations

from pydantic import BaseModel, field_validator


class AcceptHandoverRequest(BaseModel):
    signature_s3_key: str

    @field_validator("signature_s3_key")
    @classmethod
    def validate_signature(cls, v):
        if not v or not v.strip():
            raise ValueError("Signature S3 key is required")
        return v


class AcceptHandoverResponse(BaseModel):
    asset_id: str
    status: str
    signed_form_url: str
