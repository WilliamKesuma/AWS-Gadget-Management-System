from typing import Optional

from pydantic import BaseModel

from utils.pagination import ListQueryParams


class ListPendingReplacementsParams(ListQueryParams):
    history: bool = False


class PendingReplacementListItem(BaseModel):
    asset_id: str
    issue_id: str
    issue_description: str
    reported_by: str
    reported_by_id: str
    created_at: str
    resolved_by: Optional[str] = None
    resolved_by_id: Optional[str] = None
    resolved_at: Optional[str] = None
    replacement_justification: Optional[str] = None
    status: str
    management_reviewed_by: Optional[str] = None
    management_reviewed_by_id: Optional[str] = None
    management_reviewed_at: Optional[str] = None
    management_rejection_reason: Optional[str] = None
    management_remarks: Optional[str] = None
