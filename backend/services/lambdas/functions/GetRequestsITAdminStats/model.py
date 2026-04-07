from pydantic import BaseModel


class RequestsITAdminStatsResponse(BaseModel):
    completed_today: int
    total_active_requests: int
    pending_returns: int
