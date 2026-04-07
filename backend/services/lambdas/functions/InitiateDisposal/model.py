from __future__ import annotations

from pydantic import BaseModel, field_validator


class InitiateDisposalRequest(BaseModel):
    disposal_reason: str
    justification: str

    @field_validator("disposal_reason")
    @classmethod
    def validate_disposal_reason(cls, v):
        if not v or not v.strip():
            raise ValueError("DisposalReason is required")
        return v

    @field_validator("justification")
    @classmethod
    def validate_justification(cls, v):
        if not v or not v.strip():
            raise ValueError("Justification is required")
        return v


class InitiateDisposalResponse(BaseModel):
    asset_id: str
    disposal_id: str
    status: str
