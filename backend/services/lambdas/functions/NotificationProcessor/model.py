from typing import Optional

from pydantic import BaseModel


class StreamRecordData(BaseModel):
    """Parsed data from a single DynamoDB stream record."""

    event_name: str  # INSERT | MODIFY | REMOVE
    entity_prefix: str  # SK prefix: METADATA, ISSUE#, SOFTWARE#, HANDOVER#, etc.
    old_image: Optional[dict] = None
    new_image: Optional[dict] = None


class NotificationItem(BaseModel):
    """Data needed to create a single notification record in DynamoDB."""

    recipient_user_id: str
    notification_type: str
    title: str
    message: str
    reference_id: str
    reference_type: str
