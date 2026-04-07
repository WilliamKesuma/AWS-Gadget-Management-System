from pydantic import BaseModel


class RecentActivityItem(BaseModel):
    activity_id: str
    activity: str
    activity_type: str
    actor_name: str
    actor_role: str
    target_id: str
    target_type: str
    timestamp: str


class RecentActivityResponse(BaseModel):
    items: list[RecentActivityItem]
