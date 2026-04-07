from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from utils.enums import Return_Condition_Enum, Return_Trigger_Enum
from utils.pagination import ListQueryParams


class ListReturnsParams(ListQueryParams):
    return_trigger: Optional[Return_Trigger_Enum] = None
    condition_assessment: Optional[Return_Condition_Enum] = None


class ReturnListItem(BaseModel):
    asset_id: str
    return_id: str
    return_trigger: str
    initiated_by: str
    initiated_by_id: str
    initiated_at: str
    condition_assessment: str
    remarks: str
    reset_status: str
    resolved_status: Optional[str] = None
    completed_at: Optional[str] = None
