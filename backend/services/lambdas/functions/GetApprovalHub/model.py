from pydantic import BaseModel


class ApprovalHubItem(BaseModel):
    approval_type: str
    target_id: str
    title: str
    subtitle: str
    requester_name: str
    created_at: str


class ApprovalHubResponse(BaseModel):
    items: list[ApprovalHubItem]
