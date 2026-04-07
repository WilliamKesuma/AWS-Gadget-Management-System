from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class ManagementReviewRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None


class ManagementReviewResponse(BaseModel):
    asset_id: str
    disposal_id: str
    status: str
