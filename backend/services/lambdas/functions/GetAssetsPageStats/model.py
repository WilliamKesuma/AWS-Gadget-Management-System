from pydantic import BaseModel


class AssetsPageStatsResponse(BaseModel):
    total_assets: int
    in_stock: int
    assigned: int
    in_maintenance: int
