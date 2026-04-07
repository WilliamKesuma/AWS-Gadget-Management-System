from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class PendingSignatureItem(BaseModel):
    document_type: Literal["handover", "return"]
    asset_id: str
    record_id: str  # HandoverID (timestamp) for handover, ReturnID (UUID) for return

    # Handover-specific
    employee_name: Optional[str] = None
    assignment_date: Optional[str] = None
    handover_form_s3_key: Optional[str] = None

    # Return-specific
    return_trigger: Optional[str] = None
    initiated_at: Optional[str] = None
