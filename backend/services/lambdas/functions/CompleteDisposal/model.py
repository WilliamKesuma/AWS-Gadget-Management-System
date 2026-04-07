from __future__ import annotations

from pydantic import BaseModel, field_validator


class CompleteDisposalRequest(BaseModel):
    disposal_date: str
    data_wipe_confirmed: bool

    @field_validator("disposal_date")
    @classmethod
    def validate_disposal_date(cls, v):
        if not v or not v.strip():
            raise ValueError("DisposalDate is required")
        return v


class CompleteDisposalResponse(BaseModel):
    asset_id: str
    disposal_id: str
    status: str
    finance_notification_status: str
