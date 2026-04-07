from typing import Optional
from pydantic import BaseModel


class GetSoftwareRequestResponse(BaseModel):
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
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    management_reviewed_by: Optional[str] = None
    management_reviewed_by_id: Optional[str] = None
    management_reviewed_at: Optional[str] = None
    management_rejection_reason: Optional[str] = None
    management_remarks: Optional[str] = None
    created_at: str
    installation_timestamp: Optional[str] = None
