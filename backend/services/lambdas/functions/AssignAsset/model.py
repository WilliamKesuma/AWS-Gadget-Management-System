from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AssignAssetRequest(BaseModel):
    employee_id: str
    notes: Optional[str] = None


class AssignAssetResponse(BaseModel):
    asset_id: str
    employee_id: str
    assignment_date: str
    status: str
    presigned_url: str
