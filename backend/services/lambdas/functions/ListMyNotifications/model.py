from typing import Optional

from pydantic import BaseModel

from utils.pagination import ListQueryParams


class ListMyNotificationsParams(ListQueryParams):
    is_read: Optional[bool] = None


class NotificationListItem(BaseModel):
    notification_id: str
    notification_type: str
    title: str
    message: str
    reference_id: str
    reference_type: str
    is_read: bool
    created_at: str
