from __future__ import annotations

from pydantic import BaseModel


class CompleteReturnRequest(BaseModel):
    user_signature_s3_key: str


class CompleteReturnResponse(BaseModel):
    asset_id: str
    new_status: str
    completed_at: str
