from __future__ import annotations

from pydantic import BaseModel

from utils.enums import User_Role_Enum


class CreateUserRequest(BaseModel):
    fullname: str
    email: str
    role: User_Role_Enum
    initial_password: str


class CreateUserResponse(BaseModel):
    user_id: str
    role: str
    status: str
