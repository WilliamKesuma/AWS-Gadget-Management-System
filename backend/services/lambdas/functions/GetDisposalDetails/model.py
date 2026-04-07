from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AssetSpecs(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    product_description: Optional[str] = None
    cost: Optional[float] = None
    purchase_date: Optional[str] = None


class GetDisposalDetailsResponse(BaseModel):
    asset_id: str
    disposal_id: str
    status: str
    disposal_reason: str
    justification: str
    asset_specs: Optional[AssetSpecs] = None
    initiated_by: str
    initiated_by_id: str
    initiated_at: str
    management_reviewed_by: Optional[str] = None
    management_reviewed_by_id: Optional[str] = None
    management_reviewed_at: Optional[str] = None
    management_approved_at: Optional[str] = None
    management_rejection_reason: Optional[str] = None
    management_remarks: Optional[str] = None
    disposal_date: Optional[str] = None
    data_wipe_confirmed: Optional[bool] = None
    completed_by: Optional[str] = None
    completed_by_id: Optional[str] = None
    completed_at: Optional[str] = None
    is_locked: bool = False
    finance_notified_at: Optional[str] = None
    finance_notification_sent: bool = False
    finance_notification_status: Optional[str] = None
