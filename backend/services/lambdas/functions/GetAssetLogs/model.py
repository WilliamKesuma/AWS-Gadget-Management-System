from typing import Optional
from pydantic import BaseModel


class AuditLogItem(BaseModel):
    actor_id: str
    actor_name: str
    phase: str
    previous_status: str
    new_status: str
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None
    timestamp: str
