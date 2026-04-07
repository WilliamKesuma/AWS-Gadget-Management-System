from typing import Literal, Optional
from pydantic import BaseModel, model_validator


class ApproveAssetRequest(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_rejection(self):
        if self.action == "REJECT" and not (self.rejection_reason or "").strip():
            raise ValueError("Rejection reason is required")
        return self


class ApproveAssetResponse(BaseModel):
    asset_id: str
    status: str
