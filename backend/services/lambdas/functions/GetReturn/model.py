from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class GetReturnResponse(BaseModel):
    asset_id: str
    return_id: str
    return_trigger: str
    initiated_by: str
    initiated_by_id: str
    initiated_at: str
    # Set at initiation
    condition_assessment: str
    remarks: str
    reset_status: str
    serial_number: Optional[str] = None
    model: Optional[str] = None
    # Admin evidence (populated after GenerateReturnUploadUrls + SubmitAdminEvidence)
    return_photo_urls: Optional[list[str]] = None
    admin_signature_url: Optional[str] = None
    # Employee evidence (populated after CompleteReturn)
    user_signature_url: Optional[str] = None
    completed_at: Optional[str] = None
    completed_by: Optional[str] = None
    completed_by_id: Optional[str] = None
    resolved_status: Optional[str] = None
    asset_status: str
