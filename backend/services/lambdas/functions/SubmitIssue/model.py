from pydantic import BaseModel, field_validator
from utils.enums import Issue_Category_Enum


class SubmitIssueRequest(BaseModel):
    issue_description: str
    category: Issue_Category_Enum

    @field_validator("issue_description")
    @classmethod
    def not_empty(cls, v, info):
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v.strip()


class SubmitIssueResponse(BaseModel):
    asset_id: str
    issue_id: str
    status: str
