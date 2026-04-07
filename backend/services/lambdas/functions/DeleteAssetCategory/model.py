from pydantic import BaseModel


class DeleteAssetCategoryResponse(BaseModel):
    category_id: str
    message: str
