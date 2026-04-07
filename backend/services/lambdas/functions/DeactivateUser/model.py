from __future__ import annotations

from pydantic import BaseModel


class DeactivateUserResponse(BaseModel):
    user_id: str
    status: str
    message: str
