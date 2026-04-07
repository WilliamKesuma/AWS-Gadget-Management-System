from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from utils.enums import Email_Event_Type_Enum


class EmailNotificationMessage(BaseModel):
    """Unified SQS message body for all email notifications."""

    event_type: Email_Event_Type_Enum

    # Common fields
    asset_id: Optional[str] = None

    # Actor context (who triggered the event)
    actor_name: Optional[str] = None
    actor_id: Optional[str] = None

    # Issue management fields
    issue_description: Optional[str] = None
    replacement_justification: Optional[str] = None

    # Software governance fields
    software_name: Optional[str] = None

    # Return process fields
    employee_email: Optional[str] = None
    employee_name: Optional[str] = None
    asset_model: Optional[str] = None
    asset_serial: Optional[str] = None

    # Disposal fields
    disposal_id: Optional[str] = None
    disposal_reason: Optional[str] = None
    justification: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
