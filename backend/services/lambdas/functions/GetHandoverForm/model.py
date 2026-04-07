from __future__ import annotations

from pydantic import BaseModel


class GetHandoverFormResponse(BaseModel):
    asset_id: str
    presigned_url: str
