from typing import Optional

from pydantic import BaseModel


class CompleteRepairRequest(BaseModel):
    completion_notes: Optional[str] = None


class CompleteRepairResponse(BaseModel):
    asset_id: str
    issue_id: str
    status: str
