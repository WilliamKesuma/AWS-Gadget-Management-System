"""
S3 upload validation helpers.

All Lambda functions that consume uploaded files MUST use these helpers
instead of calling head_object directly. The "validate_and_clean" variants
also remove stale DynamoDB keys when the corresponding S3 object is missing,
keeping the database consistent with actual S3 state.

Usage
-----
Single key (no cleanup):
    from utils.s3_helper import validate_s3_key
    validate_s3_key(bucket, key, "Admin signature")

List of keys (no cleanup):
    from utils.s3_helper import validate_s3_keys
    validate_s3_keys(bucket, keys, "Return photos")

Single key with DynamoDB cleanup:
    from utils.s3_helper import validate_and_clean_s3_key
    validate_and_clean_s3_key(table, pk, sk, "AdminSignatureS3Key", bucket, key)

List of keys with DynamoDB cleanup:
    from utils.s3_helper import validate_and_clean_s3_keys
    validate_and_clean_s3_keys(table, pk, sk, "ReturnPhotoS3Keys", bucket, keys)
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

_s3 = boto3.client("s3")


# ---------------------------------------------------------------------------
# Low-level probe
# ---------------------------------------------------------------------------


def file_exists(bucket: str, key: str) -> bool:
    """Return True if the S3 object exists, False otherwise."""
    try:
        _s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


# ---------------------------------------------------------------------------
# Validate only (no DynamoDB side-effects)
# ---------------------------------------------------------------------------


def validate_s3_key(bucket: str, key: str | None, field_label: str) -> None:
    """
    Raise ValueError if *key* is falsy or the S3 object does not exist.

    Args:
        bucket:      S3 bucket name.
        key:         S3 object key stored in DynamoDB (may be None/empty).
        field_label: Human-readable name used in the error message,
                     e.g. "Admin signature" or "Handover form".
    """
    if not key:
        raise ValueError(f"{field_label} has not been uploaded")
    if not file_exists(bucket, key):
        raise ValueError(f"{field_label} has not been uploaded")


def validate_s3_keys(bucket: str, keys: list[str] | None, field_label: str) -> None:
    """
    Raise ValueError if *keys* is empty/None or any object does not exist in S3.

    Args:
        bucket:      S3 bucket name.
        keys:        List of S3 object keys stored in DynamoDB.
        field_label: Human-readable name used in the error message,
                     e.g. "Return photos".
    """
    if not keys:
        raise ValueError(f"{field_label} has not been uploaded")
    for key in keys:
        if not file_exists(bucket, key):
            raise ValueError(f"{field_label} has not been uploaded")


# ---------------------------------------------------------------------------
# Validate + clean stale DynamoDB keys
# ---------------------------------------------------------------------------


def validate_and_clean_s3_key(
    table,
    pk: str,
    sk: str,
    ddb_field: str,
    bucket: str,
    key: str | None,
    field_label: str | None = None,
) -> None:
    """
    Validate that *key* exists in S3.  If the key is present in DynamoDB but
    the S3 object is missing, remove the attribute from the DynamoDB record
    before raising ValueError so the client can re-upload.

    Args:
        table:       boto3 DynamoDB Table resource.
        pk:          Partition key of the DynamoDB record to clean.
        sk:          Sort key of the DynamoDB record to clean.
        ddb_field:   Attribute name to remove when the file is missing,
                     e.g. "AdminSignatureS3Key".
        bucket:      S3 bucket name.
        key:         S3 object key stored in DynamoDB (may be None/empty).
        field_label: Human-readable label for error messages.
                     Defaults to *ddb_field* when omitted.
    """
    label = field_label or ddb_field
    if not key:
        raise ValueError(f"{label} has not been uploaded")
    if not file_exists(bucket, key):
        # Key is recorded in DynamoDB but the file is gone — clean it up.
        table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="REMOVE #field",
            ExpressionAttributeNames={"#field": ddb_field},
        )
        raise ValueError(f"{label} has not been uploaded")


def validate_and_clean_s3_keys(
    table,
    pk: str,
    sk: str,
    ddb_field: str,
    bucket: str,
    keys: list[str] | None,
    field_label: str | None = None,
) -> None:
    """
    Validate that every key in *keys* exists in S3.  If the list is stored in
    DynamoDB but one or more objects are missing, remove the entire list
    attribute from the DynamoDB record before raising ValueError.

    Args:
        table:       boto3 DynamoDB Table resource.
        pk:          Partition key of the DynamoDB record to clean.
        sk:          Sort key of the DynamoDB record to clean.
        ddb_field:   Attribute name to remove when any file is missing,
                     e.g. "ReturnPhotoS3Keys".
        bucket:      S3 bucket name.
        keys:        List of S3 object keys stored in DynamoDB.
        field_label: Human-readable label for error messages.
                     Defaults to *ddb_field* when omitted.
    """
    label = field_label or ddb_field
    if not keys:
        raise ValueError(f"{label} has not been uploaded")
    missing = [k for k in keys if not file_exists(bucket, k)]
    if missing:
        table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="REMOVE #field",
            ExpressionAttributeNames={"#field": ddb_field},
        )
        raise ValueError(f"{label} has not been uploaded")
