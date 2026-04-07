from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from utils.pagination import ListQueryParams


class ListEmployeeSignaturesParams(ListQueryParams):
    assignment_date_from: Optional[str] = None
    assignment_date_to: Optional[str] = None

    @field_validator("assignment_date_from", "assignment_date_to", mode="before")
    @classmethod
    def validate_iso_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class SignatureItem(BaseModel):
    asset_id: str
    brand: Optional[str] = None
    model: Optional[str] = None
    assignment_date: str
    signature_timestamp: str
    signature_url: str
