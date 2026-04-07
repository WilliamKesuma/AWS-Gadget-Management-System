from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from utils.enums import Return_Condition_Enum, Return_Trigger_Enum
from utils.pagination import ListQueryParams


class ListAllReturnsParams(ListQueryParams):
    status: Optional[str] = None
    return_trigger: Optional[Return_Trigger_Enum] = None
    condition_assessment: Optional[Return_Condition_Enum] = None
    history: bool = False
    asset_id: Optional[str] = None


class AllReturnListItem(BaseModel):
    asset_id: str
    return_id: str
    return_trigger: str
    initiated_by: str
    initiated_by_id: str
    initiated_at: str
    condition_assessment: str
    remarks: str
    reset_status: str
    serial_number: Optional[str] = None
    model: Optional[str] = None
    resolved_status: Optional[str] = None
    completed_at: Optional[str] = None
    completed_by: Optional[str] = None
    completed_by_id: Optional[str] = None
