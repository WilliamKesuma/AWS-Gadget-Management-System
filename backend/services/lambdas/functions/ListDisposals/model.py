from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from utils.pagination import ListQueryParams


class ListDisposalsParams(ListQueryParams):
    disposal_reason: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    history: bool = False
    asset_id: Optional[str] = None

    @field_validator("date_from", "date_to", mode="before")
    @classmethod
    def validate_iso_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class DisposalListItem(BaseModel):
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
