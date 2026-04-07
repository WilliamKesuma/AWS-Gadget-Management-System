from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator

from utils.enums import Asset_Status_Enum
from utils.pagination import ListQueryParams


class ListAssetsParams(ListQueryParams):
    status: Optional[Asset_Status_Enum] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model_name: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    @field_validator("date_from", "date_to", mode="before")
    @classmethod
    def validate_date_format(cls, v):
        if v is not None and v != "":
            # Basic ISO date format check (YYYY-MM-DD)
            import re

            if not re.match(r"^\d{4}-\d{2}-\d{2}", v):
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v or None


class AssetItem(BaseModel):
    asset_id: str
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    status: str
    category: Optional[str] = None
    assignment_date: Optional[str] = None
    condition: Optional[str] = None
    created_at: Optional[str] = None
