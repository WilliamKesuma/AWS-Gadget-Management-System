from __future__ import annotations

from pydantic import BaseModel


class GetSignedHandoverFormResponse(BaseModel):
    asset_id: str
    presigned_url: str
