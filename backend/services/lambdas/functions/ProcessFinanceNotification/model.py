from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class FinanceNotificationMessage(BaseModel):
    """SQS message body model for finance notification payload."""

    asset_id: str
    serial_number: Optional[str] = None
    purchase_date: Optional[str] = None
    original_cost: Optional[float] = None
    disposal_date: str
    disposal_reason: str
