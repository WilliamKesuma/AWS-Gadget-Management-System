from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AssigneeInfo(BaseModel):
    user_id: str
    fullname: str
    role: str


class GetAssetResponse(BaseModel):
    asset_id: str
    invoice_number: Optional[str] = None
    vendor: Optional[str] = None
    purchase_date: Optional[str] = None
    serial_number: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    product_description: Optional[str] = None
    cost: Optional[float] = None
    payment_method: Optional[str] = None
    processor: Optional[str] = None
    storage: Optional[str] = None
    os_version: Optional[str] = None
    memory: Optional[str] = None
    invoice_url: Optional[str] = None
    gadget_photo_urls: Optional[list[str]] = None
    status: str
    category: Optional[str] = None
    condition: Optional[str] = None
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[str] = None
    assigned_date: Optional[str] = None
    assignee: Optional[AssigneeInfo] = None
