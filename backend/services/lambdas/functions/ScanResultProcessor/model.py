from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TextractSNSMessage(BaseModel):
    """Parsed Textract completion message from SNS."""

    JobId: str
    Status: str
    API: str
    JobTag: Optional[str] = None
    Timestamp: Optional[int] = None
