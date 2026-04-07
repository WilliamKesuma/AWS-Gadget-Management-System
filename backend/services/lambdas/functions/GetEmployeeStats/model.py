from pydantic import BaseModel


class EmployeeStatsResponse(BaseModel):
    my_pending_requests: int
    assigned_assets: int
    pending_signatures: int
