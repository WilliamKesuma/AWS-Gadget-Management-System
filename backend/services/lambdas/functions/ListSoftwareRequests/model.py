from typing import Optional

from pydantic import BaseModel

from utils.enums import Software_Status_Enum, Data_Access_Impact_Enum
from utils.pagination import ListQueryParams


class ListSoftwareRequestsParams(ListQueryParams):
    status: Optional[Software_Status_Enum] = None
    risk_level: Optional[str] = None
    software_name: Optional[str] = None
    vendor: Optional[str] = None
    license_validity_period: Optional[str] = None
    data_access_impact: Optional[Data_Access_Impact_Enum] = None


class SoftwareRequestListItem(BaseModel):
    asset_id: str
    software_request_id: str
    software_name: str
    version: str
    vendor: str
    justification: str
    license_type: str
    license_validity_period: str
    data_access_impact: str
    status: str
    risk_level: Optional[str] = None
    requested_by: str
    requested_by_id: str
    reviewed_by: Optional[str] = None
    reviewed_by_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: str
    reviewed_at: Optional[str] = None
