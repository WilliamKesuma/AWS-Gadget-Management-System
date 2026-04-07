from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, field_validator

from utils.enums import User_Role_Enum, User_Status_Enum
from utils.pagination import ListQueryParams


class ListUsersParams(ListQueryParams):
    role: Optional[User_Role_Enum] = None
    status: Optional[str] = None
    name: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid = {User_Status_Enum.ACTIVE.value, User_Status_Enum.INACTIVE.value}
        if v is not None and v not in valid:
            raise ValueError("Invalid status. Must be one of: active, inactive")
        return v


class UserItem(BaseModel):
    user_id: str
    fullname: str
    email: str
    role: str
    status: str
    created_at: str
