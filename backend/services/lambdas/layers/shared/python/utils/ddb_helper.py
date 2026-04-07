from boto3.dynamodb.conditions import ConditionBase
from typing import Optional


def get_item(table, key: dict) -> Optional[dict]:
    response = table.get_item(Key=key)
    return response.get("Item")


def put_item(table, item: dict) -> None:
    table.put_item(Item=item)


def update_item(table, key: dict, updates: dict) -> dict:
    update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
    expr_names = {f"#{k}": k for k in updates}
    expr_values = {f":{k}": v for k, v in updates.items()}

    response = table.update_item(
        Key=key,
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )
    return response.get("Attributes", {})


def delete_item(table, key: dict) -> None:
    table.delete_item(Key=key)


def query_index(
    table,
    index_name: str,
    key_condition: ConditionBase,
    filter_exp: Optional[ConditionBase] = None,
) -> list:
    kwargs = {
        "IndexName": index_name,
        "KeyConditionExpression": key_condition,
    }
    if filter_exp is not None:
        kwargs["FilterExpression"] = filter_exp

    response = table.query(**kwargs)
    return response.get("Items", [])


def paginated_query(
    table,
    index_name: str | None,
    key_condition: ConditionBase,
    filter_exp: ConditionBase | None = None,
    scan_index_forward: bool = False,
    cursor: str | None = None,
) -> tuple[list[dict], str | None]:
    """Execute a cursor-based paginated DynamoDB query.

    Uses DynamoDB's native LastEvaluatedKey for O(1) pagination per page,
    regardless of dataset size. Page size is fixed at PAGE_SIZE (20).

    Args:
        cursor: Opaque cursor string from a previous response (base64-encoded
                LastEvaluatedKey). None for the first page.

    Returns: (items, next_cursor)
        - items: up to PAGE_SIZE items for this page
        - next_cursor: opaque string for the next page, or None if no more pages
    """
    from utils.pagination import PAGE_SIZE, encode_cursor, decode_cursor

    data_kwargs: dict = {
        "KeyConditionExpression": key_condition,
        "ScanIndexForward": scan_index_forward,
        "Limit": PAGE_SIZE,
    }
    if index_name is not None:
        data_kwargs["IndexName"] = index_name
    if filter_exp is not None:
        data_kwargs["FilterExpression"] = filter_exp
    if cursor:
        data_kwargs["ExclusiveStartKey"] = decode_cursor(cursor)

    items: list[dict] = []

    # When FilterExpression is used, DynamoDB may return fewer than Limit items
    # because filtering happens after the Limit is applied. We loop until we
    # have enough items or exhaust the dataset.
    while len(items) < PAGE_SIZE:
        data_kwargs["Limit"] = PAGE_SIZE - len(items)
        response = table.query(**data_kwargs)
        page_items = response.get("Items", [])
        items.extend(page_items)

        if "LastEvaluatedKey" not in response:
            # No more data in DynamoDB
            return (items, None)

        data_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    # We have PAGE_SIZE items. The ExclusiveStartKey from the last response
    # is our cursor for the next page.
    last_key = response.get("LastEvaluatedKey")
    next_cursor = encode_cursor(last_key) if last_key else None

    return (items, next_cursor)
