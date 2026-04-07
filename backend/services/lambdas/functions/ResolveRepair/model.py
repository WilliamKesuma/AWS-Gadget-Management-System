from typing import Optional

from pydantic import BaseModel


class ResolveRepairRequest(BaseModel):
    repair_notes: Optional[str] = None


class ResolveRepairResponse(BaseModel):
    asset_id: str
    issue_id: str
    status: str
