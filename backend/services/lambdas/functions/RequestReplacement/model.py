from pydantic import BaseModel, field_validator


class RequestReplacementRequest(BaseModel):
    replacement_justification: str

    @field_validator("replacement_justification")
    @classmethod
    def not_empty(cls, v, info):
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v.strip()


class RequestReplacementResponse(BaseModel):
    asset_id: str
    issue_id: str
    status: str
