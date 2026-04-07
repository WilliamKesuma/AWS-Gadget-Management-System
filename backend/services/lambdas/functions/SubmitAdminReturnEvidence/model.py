from __future__ import annotations

from pydantic import BaseModel


class SubmitAdminReturnEvidenceResponse(BaseModel):
    asset_id: str
    return_id: str
    message: str
