from custom_exceptions import ConflictException

LOCK_MESSAGES = {
    "asset": "This asset record is permanently locked and cannot be modified",
    "disposal": "This disposal record is permanently locked and cannot be modified",
}


def check_record_lock(item: dict, record_type: str = "asset") -> None:
    """Check if a DynamoDB item is locked and raise ConflictException if so.

    This should be called as the first validation step before processing
    any update operation on an Asset_Record or Disposal_Record.

    Args:
        item: The DynamoDB item dict to check.
        record_type: Either "asset" or "disposal" to select the error message.

    Raises:
        ConflictException: If the item has IsLocked set to True.
    """
    if item.get("IsLocked") is True:
        message = LOCK_MESSAGES.get(record_type, LOCK_MESSAGES["asset"])
        raise ConflictException(message)
