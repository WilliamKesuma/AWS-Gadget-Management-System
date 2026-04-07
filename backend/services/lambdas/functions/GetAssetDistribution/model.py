from pydantic import BaseModel


class AssetDistributionItem(BaseModel):
    category: str
    count: int


class AssetDistributionResponse(BaseModel):
    items: list[AssetDistributionItem]
