from pydantic import BaseModel


class FinanceStatsResponse(BaseModel):
    total_disposed: int
    total_asset_value: int
