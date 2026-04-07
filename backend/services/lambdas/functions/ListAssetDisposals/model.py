from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from utils.pagination import ListQueryParams


class ListAssetDisposalsParams(ListQueryParams):
    status: Optional[str] = None


class AssetDisposalListItem(BaseModel):
    asset_id: str
    disposal_id: str
    disposal_reason: str
    justification: str
    initiated_by: str
    initiated_by_id: str
    initiated_at: str
    status: str
    management_reviewed_by: Optional[str] = None
    management_reviewed_by_id: Optional[str] = None
    management_reviewed_at: Optional[str] = None
    management_rejection_reason: Optional[str] = None
    disposal_date: Optional[str] = None
    data_wipe_confirmed: Optional[bool] = None
