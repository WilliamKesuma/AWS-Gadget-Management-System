from typing import Optional

from pydantic import BaseModel

from utils.enums import Issue_Status_Enum, Issue_Category_Enum
from utils.pagination import ListQueryParams


class ListAllIssuesParams(ListQueryParams):
    status: Optional[Issue_Status_Enum] = None
    category: Optional[Issue_Category_Enum] = None
    history: bool = False
    asset_id: Optional[str] = None


class AllIssueListItem(BaseModel):
    asset_id: str
    issue_id: str
    issue_description: str
    category: str
    status: str
    action_path: Optional[str] = None
    reported_by: str
    reported_by_id: str
    created_at: str
    resolved_by: Optional[str] = None
    resolved_by_id: Optional[str] = None
    resolved_at: Optional[str] = None
    repair_notes: Optional[str] = None
    warranty_notes: Optional[str] = None
    warranty_sent_at: Optional[str] = None
    replacement_justification: Optional[str] = None
    management_reviewed_by: Optional[str] = None
    management_reviewed_by_id: Optional[str] = None
    management_reviewed_at: Optional[str] = None
    management_rejection_reason: Optional[str] = None
    management_remarks: Optional[str] = None
    completed_at: Optional[str] = None
    completion_notes: Optional[str] = None
