from pydantic import BaseModel


class RequestsEmployeeStatsResponse(BaseModel):
    active_requests: int
    pending_approval: int
    resolved_monthly: int
