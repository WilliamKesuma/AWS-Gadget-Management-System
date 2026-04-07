from __future__ import annotations

from pydantic import BaseModel, field_validator

from utils.enums import Return_Condition_Enum, Reset_Status_Enum, Return_Trigger_Enum


class InitiateReturnRequest(BaseModel):
    return_trigger: str
    remarks: str
    condition_assessment: str
    reset_status: str

    @field_validator("return_trigger")
    @classmethod
    def validate_trigger(cls, v):
        valid = {e.value for e in Return_Trigger_Enum}
        if v not in valid:
            raise ValueError(
                "Invalid return trigger. Must be one of: RESIGNATION, REPLACEMENT, TRANSFER, IT_RECALL, UPGRADE"
            )
        return v

    @field_validator("condition_assessment")
    @classmethod
    def validate_condition(cls, v):
        valid = {e.value for e in Return_Condition_Enum}
        if v not in valid:
            raise ValueError(
                "Invalid condition assessment. Must be one of: GOOD, MINOR_DAMAGE, MINOR_DAMAGE_REPAIR_REQUIRED, MAJOR_DAMAGE"
            )
        return v

    @field_validator("reset_status")
    @classmethod
    def validate_reset(cls, v):
        valid = {e.value for e in Reset_Status_Enum}
        if v not in valid:
            raise ValueError(
                "Invalid reset status. Must be one of: COMPLETE, INCOMPLETE"
            )
        return v


class InitiateReturnResponse(BaseModel):
    asset_id: str
    return_id: str
    status: str
