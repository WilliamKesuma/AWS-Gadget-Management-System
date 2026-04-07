from typing import Optional, Literal
from pydantic import BaseModel, model_validator


class ManagementReviewIssueRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_rejection_reason(self):
        if self.decision == "REJECT" and (
            not self.rejection_reason or not self.rejection_reason.strip()
        ):
            raise ValueError("Rejection reason is required")
        return self


class ManagementReviewIssueResponse(BaseModel):
    asset_id: str
    issue_id: str
    status: str
