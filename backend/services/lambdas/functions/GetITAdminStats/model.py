from pydantic import BaseModel


class ITAdminStatsResponse(BaseModel):
    total_assets: int
    pending_issues: int
    in_maintenance: int
