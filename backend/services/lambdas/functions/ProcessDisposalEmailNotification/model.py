from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from utils.enums import Disposal_Email_Event_Type_Enum


class DisposalEmailNotificationMessage(BaseModel):
    """SQS message body for disposal email notifications."""

    event_type: Disposal_Email_Event_Type_Enum
    asset_id: str
    disposal_id: str
    disposal_reason: str
    justification: str
    # Asset snapshot fields
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    # Populated only for DISPOSAL_MANAGEMENT_APPROVED
    initiated_by_name: Optional[str] = None
