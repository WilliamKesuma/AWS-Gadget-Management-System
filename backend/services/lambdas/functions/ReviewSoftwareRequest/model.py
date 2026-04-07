from typing import Optional, Literal
from pydantic import BaseModel, model_validator

from utils.enums import Risk_Level_Enum


class ReviewSoftwareRequestRequest(BaseModel):
    decision: Literal["APPROVE", "ESCALATE", "REJECT"]
    risk_level: Risk_Level_Enum
    rejection_reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_decision_rules(self):
        if self.decision == "APPROVE" and self.risk_level in (
            Risk_Level_Enum.MEDIUM,
            Risk_Level_Enum.HIGH,
        ):
            raise ValueError(
                "MEDIUM and HIGH risk requests must be escalated to Management"
            )
        if self.decision == "ESCALATE" and self.risk_level == Risk_Level_Enum.LOW:
            raise ValueError(
                "Low risk requests cannot be escalated; approve or reject directly"
            )
        if self.decision == "REJECT" and (
            not self.rejection_reason or not self.rejection_reason.strip()
        ):
            raise ValueError("Rejection reason is required")
        return self


class ReviewSoftwareRequestResponse(BaseModel):
    asset_id: str
    software_request_id: str
    status: str
    risk_level: str
