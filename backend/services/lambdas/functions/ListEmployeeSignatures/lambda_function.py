import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from custom_exceptions import NotFoundException, ConflictException
from utils import success, error, get_item
from utils.auth import require_group
from utils.enums import User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query

from model import ListEmployeeSignaturesParams, SignatureItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
s3_client = boto3.client("s3")


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        employee_id = event["pathParameters"]["id"]

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        # Verify employee exists
        employee_item = get_item(table, {"PK": f"USER#{employee_id}", "SK": "METADATA"})
        if not employee_item:
            raise NotFoundException("Employee not found")

        try:
            query_params = ListEmployeeSignaturesParams(
                sort_order=params.get("sort_order", "desc"),
                assignment_date_from=params.get("assignment_date_from"),
                assignment_date_to=params.get("assignment_date_to"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        # Query EmployeeAssetIndex GSI for assets assigned to this employee
        key_condition = Key("EmployeeAssetIndexPK").eq(f"EMPLOYEE#{employee_id}")

        items, next_cursor = paginated_query(
            table,
            "EmployeeAssetIndex",
            key_condition,
            cursor=pagination.cursor,
            scan_index_forward=scan_index_forward,
        )

        signatures = []
        for item in items:
            # Extract asset_id from PK (strip "ASSET#" prefix)
            asset_id = item["PK"].replace("ASSET#", "")

            # Extract assignment_date from EmployeeAssetIndexSK (strip "ASSET#" prefix)
            assignment_date = item.get("EmployeeAssetIndexSK", "").replace("ASSET#", "")

            # Post-fetch date range filtering (lexicographic ISO 8601 comparison)
            if (
                query_params.assignment_date_from
                and assignment_date < query_params.assignment_date_from
            ):
                continue
            if (
                query_params.assignment_date_to
                and assignment_date > query_params.assignment_date_to
            ):
                continue

            # Query for Handover_Records with SignatureS3Key
            handover_results = table.query(
                KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
                & Key("SK").begins_with("HANDOVER#"),
            )["Items"]

            for handover in handover_results:
                signature_s3_key = handover.get("SignatureS3Key")
                if not signature_s3_key:
                    continue

                # Fetch asset details
                asset_item = get_item(
                    table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"}
                )
                if not asset_item:
                    continue

                # Generate presigned GET URL (60 min TTL)
                signature_url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": ASSETS_BUCKET, "Key": signature_s3_key},
                    ExpiresIn=3600,
                )

                # Use AcceptedAt for signature_timestamp, fallback to assignment_date
                signature_timestamp = handover.get("AcceptedAt", assignment_date)

                signatures.append(
                    SignatureItem(
                        asset_id=asset_id,
                        brand=asset_item.get("Brand"),
                        model=asset_item.get("Model"),
                        assignment_date=assignment_date,
                        signature_timestamp=signature_timestamp,
                        signature_url=signature_url,
                    )
                )

        response = PaginatedResponse(
            items=[item.model_dump() for item in signatures],
            count=len(signatures),
            next_cursor=next_cursor,
            has_next_page=next_cursor is not None,
        )
        return success(response.model_dump())

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except ConflictException as e:
        return error(str(e), 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
