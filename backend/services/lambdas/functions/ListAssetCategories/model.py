from pydantic import BaseModel


class CategoryItem(BaseModel):
    category_id: str
    category_name: str
    created_at: str
