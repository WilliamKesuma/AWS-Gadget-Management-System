"""
Domain-prefixed ID generator using DynamoDB atomic counters.

Format: {DOMAIN}-{YYYYMM}-{INCREMENTAL}
Examples: ISSUE-202605-1, DISPOSAL-202605-2, RETURN-202605-1, SOFTWARE-202605-3

Uses the same atomic counter pattern as asset ID generation (COUNTER# records).
Counter PK: DOMAIN_COUNTER#{domain}#{YYYYMM}  |  SK: METADATA
"""

from datetime import datetime, timezone


def generate_domain_id(table, domain: str) -> str:
    """Generate a domain-prefixed sequential ID using an atomic DynamoDB counter.

    Args:
        table: boto3 DynamoDB Table resource
        domain: Domain prefix (e.g. "ISSUE", "DISPOSAL", "RETURN", "SOFTWARE")

    Returns:
        Formatted ID like "ISSUE-202605-1"
    """
    year_month = datetime.now(timezone.utc).strftime("%Y%m")

    response = table.update_item(
        Key={"PK": f"DOMAIN_COUNTER#{domain}#{year_month}", "SK": "METADATA"},
        UpdateExpression="ADD #count :inc",
        ExpressionAttributeNames={"#count": "Count"},
        ExpressionAttributeValues={":inc": 1},
        ReturnValues="UPDATED_NEW",
    )
    count = int(response["Attributes"]["Count"])

    return f"{domain}-{year_month}-{count}"
