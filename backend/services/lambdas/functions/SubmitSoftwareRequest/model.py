from pydantic import BaseModel, field_validator

from utils.enums import Data_Access_Impact_Enum


class SubmitSoftwareRequestRequest(BaseModel):
    software_name: str
    version: str
    vendor: str
    justification: str
    license_type: str
    license_validity_period: str
    data_access_impact: Data_Access_Impact_Enum

    @field_validator(
        "software_name",
        "version",
        "vendor",
        "justification",
        "license_type",
        "license_validity_period",
    )
    @classmethod
    def not_empty(cls, v, info):
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v.strip()


class SubmitSoftwareRequestResponse(BaseModel):
    asset_id: str
    software_request_id: str
    status: str
