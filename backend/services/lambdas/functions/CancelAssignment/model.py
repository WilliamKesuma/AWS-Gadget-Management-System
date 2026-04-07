from __future__ import annotations

from pydantic import BaseModel


class CancelAssignmentResponse(BaseModel):
    asset_id: str
    status: str
