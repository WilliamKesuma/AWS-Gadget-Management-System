from pydantic import BaseModel


class MarkNotificationReadItem(BaseModel):
    notification_id: str
    notification_type: str
    title: str
    message: str
    reference_id: str
    reference_type: str
    is_read: bool
    created_at: str
