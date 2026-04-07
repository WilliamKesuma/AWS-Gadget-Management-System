from typing import Optional, Literal
from pydantic import BaseModel, model_validator


class ManagementReviewRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None

    @model_validator(mode="after")
    def validate_rejection_reason(self):
        if self.decision == "REJECT" and (
            not self.rejection_reason or not self.rejection_reason.strip()
        ):
            raise ValueError("Rejection reason is required")
        return self


class ManagementReviewResponse(BaseModel):
    asset_id: str
    software_request_id: str
    status: str
