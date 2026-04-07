import base64
import json
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Fixed page size for all paginated queries. Not client-configurable.
PAGE_SIZE = 20


class PaginationInput(BaseModel):
    cursor: Optional[str] = None

    @classmethod
    def from_query_params(cls, params: dict | None) -> "PaginationInput":
        """Parse cursor from API Gateway query string parameters."""
        if not params:
            return cls()
        return cls(cursor=params.get("cursor"))


def encode_cursor(last_evaluated_key: dict) -> str:
    """Encode a DynamoDB LastEvaluatedKey into a URL-safe opaque cursor string."""
    return base64.urlsafe_b64encode(json.dumps(last_evaluated_key).encode()).decode()


def decode_cursor(cursor: str) -> dict:
    """Decode an opaque cursor string back into a DynamoDB ExclusiveStartKey."""
    return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())


class PaginatedResponse(BaseModel):
    items: list[dict]
    count: int
    next_cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor for the next page (null if no more pages)",
    )
    has_next_page: bool = Field(
        default=False, description="Whether more pages exist after current"
    )


class ListQueryParams(BaseModel):
    """Base model for all List Lambda query parameters. Provides sort_order."""

    sort_order: Literal["asc", "desc"] = "desc"
