from __future__ import annotations

from pydantic import BaseModel


class ReactivateUserResponse(BaseModel):
    user_id: str
    status: str
    message: str
