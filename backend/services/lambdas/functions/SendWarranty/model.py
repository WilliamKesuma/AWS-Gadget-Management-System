from typing import Optional

from pydantic import BaseModel


class SendWarrantyRequest(BaseModel):
    warranty_notes: Optional[str] = None


class SendWarrantyResponse(BaseModel):
    asset_id: str
    issue_id: str
    status: str
