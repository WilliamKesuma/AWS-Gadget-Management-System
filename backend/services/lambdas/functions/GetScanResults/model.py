from typing import Optional
from pydantic import BaseModel


class GetScanResultsResponse(BaseModel):
    status: str
    extracted_fields: Optional[dict] = None
    failure_reason: Optional[str] = None
