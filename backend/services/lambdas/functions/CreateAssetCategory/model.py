from pydantic import BaseModel


class CreateAssetCategoryRequest(BaseModel):
    category_name: str


class CreateAssetCategoryResponse(BaseModel):
    category_id: str
    category_name: str
    created_at: str
