from pydantic import BaseModel


class ManagementStatsResponse(BaseModel):
    total_assets: int
    pending_approvals: int
    scheduled_disposals: int
