from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from utils.pagination import ListQueryParams


class ListPendingDisposalsParams(ListQueryParams):
    disposal_reason: Optional[str] = None
    history: bool = False


class AssetSpecs(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    product_description: Optional[str] = None
    cost: Optional[float] = None
    purchase_date: Optional[str] = None


class PendingDisposalItem(BaseModel):
    asset_id: str
    disposal_id: str
    disposal_reason: str
    justification: str
    asset_specs: Optional[AssetSpecs] = None
    initiated_by: str
    initiated_by_id: str
    initiated_at: str
    status: Optional[str] = None
    management_reviewed_by: Optional[str] = None
    management_reviewed_by_id: Optional[str] = None
    management_reviewed_at: Optional[str] = None
