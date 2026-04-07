from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class CreateAssetRequest(BaseModel):
    scan_job_id: str
    category: str
    invoice_number: str
    vendor: str
    purchase_date: str
    brand: str
    model_name: str
    cost: Decimal
    serial_number: Optional[str] = None
    product_description: Optional[str] = None
    payment_method: Optional[str] = None
    processor: Optional[str] = None
    storage: Optional[str] = None
    os_version: Optional[str] = None
    memory: Optional[str] = None


class CreateAssetResponse(BaseModel):
    asset_id: str
    status: str
