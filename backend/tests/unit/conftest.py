import json
import os
import sys

import boto3
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# Make the shared Lambda layers importable so handler code can
# ``from utils import …`` and ``from custom_exceptions import …``
# without deploying real Lambda layers.
# ---------------------------------------------------------------------------
LAYERS_PYTHON = os.path.join(
    os.path.dirname(__file__),
    os.pardir,
    os.pardir,
    "services",
    "lambdas",
    "layers",
    "shared",
    "python",
)
if LAYERS_PYTHON not in sys.path:
    sys.path.insert(0, os.path.abspath(LAYERS_PYTHON))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TABLE_NAME = "gms-dev-assets"
BUCKET_NAME = "gms-dev-assets-bucket"
USER_POOL_NAME = "gms-dev-user-pool"
REGION = "ap-southeast-1"
COGNITO_GROUPS = [
    "gms-dev-it_admin-group",
    "gms-dev-management-group",
    "gms-dev-employee-group",
    "gms-dev-finance-group",
]


# ---------------------------------------------------------------------------
# Environment variables — autouse so every test gets them
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    """Set base AWS / Lambda environment variables for all tests."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("ASSETS_TABLE", TABLE_NAME)
    monkeypatch.setenv("ASSETS_BUCKET", BUCKET_NAME)
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "test")
    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "true")


# ---------------------------------------------------------------------------
# Combined AWS mock context — Cognito + DynamoDB in a single mock_aws scope
# ---------------------------------------------------------------------------
@pytest.fixture
def aws_mocks(monkeypatch):
    """Single ``mock_aws`` context providing both Cognito and DynamoDB.

    Yields a dict with:
        - ``cognito_client``: boto3 Cognito-IDP client
        - ``user_pool_id``: ID of the moto-created User Pool
        - ``table``: boto3 DynamoDB Table resource for ``gms-dev-assets``
    """
    with mock_aws():
        # ---- Cognito User Pool + groups ----
        cognito_client = boto3.client("cognito-idp", region_name=REGION)
        pool_resp = cognito_client.create_user_pool(PoolName=USER_POOL_NAME)
        user_pool_id = pool_resp["UserPool"]["Id"]

        for group in COGNITO_GROUPS:
            cognito_client.create_group(
                GroupName=group,
                UserPoolId=user_pool_id,
            )

        monkeypatch.setenv("USER_POOL_ID", user_pool_id)

        # ---- DynamoDB table with all GSIs ----
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "EntityType", "AttributeType": "S"},
                {"AttributeName": "CreatedAt", "AttributeType": "S"},
                {"AttributeName": "StatusIndexPK", "AttributeType": "S"},
                {"AttributeName": "StatusIndexSK", "AttributeType": "S"},
                {"AttributeName": "SerialNumberIndexPK", "AttributeType": "S"},
                {"AttributeName": "SerialNumberIndexSK", "AttributeType": "S"},
                {"AttributeName": "EmployeeAssetIndexPK", "AttributeType": "S"},
                {"AttributeName": "EmployeeAssetIndexSK", "AttributeType": "S"},
                {"AttributeName": "SoftwareStatusIndexPK", "AttributeType": "S"},
                {"AttributeName": "SoftwareStatusIndexSK", "AttributeType": "S"},
                {"AttributeName": "IssueStatusIndexPK", "AttributeType": "S"},
                {"AttributeName": "IssueStatusIndexSK", "AttributeType": "S"},
                {"AttributeName": "DisposalStatusIndexPK", "AttributeType": "S"},
                {"AttributeName": "DisposalStatusIndexSK", "AttributeType": "S"},
                {"AttributeName": "DisposalEntityType", "AttributeType": "S"},
                {"AttributeName": "InitiatedAt", "AttributeType": "S"},
                {"AttributeName": "CategoryEntityType", "AttributeType": "S"},
                {"AttributeName": "CategoryNameIndexPK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "EntityTypeIndex",
                    "KeySchema": [
                        {"AttributeName": "EntityType", "KeyType": "HASH"},
                        {"AttributeName": "CreatedAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "StatusIndex",
                    "KeySchema": [
                        {"AttributeName": "StatusIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "StatusIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "SerialNumberIndex",
                    "KeySchema": [
                        {"AttributeName": "SerialNumberIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "SerialNumberIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "EmployeeAssetIndex",
                    "KeySchema": [
                        {"AttributeName": "EmployeeAssetIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "EmployeeAssetIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "SoftwareStatusIndex",
                    "KeySchema": [
                        {"AttributeName": "SoftwareStatusIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "SoftwareStatusIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "IssueStatusIndex",
                    "KeySchema": [
                        {"AttributeName": "IssueStatusIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "IssueStatusIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "DisposalStatusIndex",
                    "KeySchema": [
                        {"AttributeName": "DisposalStatusIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "DisposalStatusIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "DisposalEntityIndex",
                    "KeySchema": [
                        {"AttributeName": "DisposalEntityType", "KeyType": "HASH"},
                        {"AttributeName": "InitiatedAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "CategoryEntityIndex",
                    "KeySchema": [
                        {"AttributeName": "CategoryEntityType", "KeyType": "HASH"},
                        {"AttributeName": "CreatedAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "CategoryNameIndex",
                    "KeySchema": [
                        {"AttributeName": "CategoryNameIndexPK", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "KEYS_ONLY"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.meta.client.get_waiter("table_exists").wait(TableName=TABLE_NAME)

        # ---- S3 bucket ----
        s3_client = boto3.client("s3", region_name=REGION)
        s3_client.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )

        yield {
            "cognito_client": cognito_client,
            "user_pool_id": user_pool_id,
            "table": table,
            "s3_client": s3_client,
        }


# ---------------------------------------------------------------------------
# Standalone fixtures (for tests that only need one service)
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_cognito(monkeypatch):
    """Moto-mocked Cognito User Pool with four groups."""
    with mock_aws():
        client = boto3.client("cognito-idp", region_name=REGION)
        pool_resp = client.create_user_pool(PoolName=USER_POOL_NAME)
        user_pool_id = pool_resp["UserPool"]["Id"]

        for group in COGNITO_GROUPS:
            client.create_group(GroupName=group, UserPoolId=user_pool_id)

        monkeypatch.setenv("USER_POOL_ID", user_pool_id)

        yield {"client": client, "user_pool_id": user_pool_id}


@pytest.fixture
def mock_dynamodb():
    """Moto-mocked DynamoDB table matching ``gms-dev-assets`` schema."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "EntityType", "AttributeType": "S"},
                {"AttributeName": "CreatedAt", "AttributeType": "S"},
                {"AttributeName": "StatusIndexPK", "AttributeType": "S"},
                {"AttributeName": "StatusIndexSK", "AttributeType": "S"},
                {"AttributeName": "SerialNumberIndexPK", "AttributeType": "S"},
                {"AttributeName": "SerialNumberIndexSK", "AttributeType": "S"},
                {"AttributeName": "EmployeeAssetIndexPK", "AttributeType": "S"},
                {"AttributeName": "EmployeeAssetIndexSK", "AttributeType": "S"},
                {"AttributeName": "SoftwareStatusIndexPK", "AttributeType": "S"},
                {"AttributeName": "SoftwareStatusIndexSK", "AttributeType": "S"},
                {"AttributeName": "IssueStatusIndexPK", "AttributeType": "S"},
                {"AttributeName": "IssueStatusIndexSK", "AttributeType": "S"},
                {"AttributeName": "DisposalStatusIndexPK", "AttributeType": "S"},
                {"AttributeName": "DisposalStatusIndexSK", "AttributeType": "S"},
                {"AttributeName": "DisposalEntityType", "AttributeType": "S"},
                {"AttributeName": "InitiatedAt", "AttributeType": "S"},
                {"AttributeName": "CategoryEntityType", "AttributeType": "S"},
                {"AttributeName": "CategoryNameIndexPK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "EntityTypeIndex",
                    "KeySchema": [
                        {"AttributeName": "EntityType", "KeyType": "HASH"},
                        {"AttributeName": "CreatedAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "StatusIndex",
                    "KeySchema": [
                        {"AttributeName": "StatusIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "StatusIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "SerialNumberIndex",
                    "KeySchema": [
                        {"AttributeName": "SerialNumberIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "SerialNumberIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "EmployeeAssetIndex",
                    "KeySchema": [
                        {"AttributeName": "EmployeeAssetIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "EmployeeAssetIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "SoftwareStatusIndex",
                    "KeySchema": [
                        {"AttributeName": "SoftwareStatusIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "SoftwareStatusIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "IssueStatusIndex",
                    "KeySchema": [
                        {"AttributeName": "IssueStatusIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "IssueStatusIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "DisposalStatusIndex",
                    "KeySchema": [
                        {"AttributeName": "DisposalStatusIndexPK", "KeyType": "HASH"},
                        {"AttributeName": "DisposalStatusIndexSK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "DisposalEntityIndex",
                    "KeySchema": [
                        {"AttributeName": "DisposalEntityType", "KeyType": "HASH"},
                        {"AttributeName": "InitiatedAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "CategoryEntityIndex",
                    "KeySchema": [
                        {"AttributeName": "CategoryEntityType", "KeyType": "HASH"},
                        {"AttributeName": "CreatedAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "CategoryNameIndex",
                    "KeySchema": [
                        {"AttributeName": "CategoryNameIndexPK", "KeyType": "HASH"},
                    ],
                    "Projection": {"ProjectionType": "KEYS_ONLY"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.meta.client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
        yield table


# ---------------------------------------------------------------------------
# API Gateway event fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def it_admin_event():
    """API Gateway proxy event with valid it-admin Cognito claims."""
    return {
        "httpMethod": "POST",
        "path": "/users/create",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({}),
        "queryStringParameters": None,
        "pathParameters": None,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "admin-user-id-1234",
                    "email": "admin@example.com",
                    "cognito:groups": "it-admin",
                }
            }
        },
    }


@pytest.fixture
def non_admin_event():
    """API Gateway proxy event without it-admin claims (employee role)."""
    return {
        "httpMethod": "POST",
        "path": "/users/create",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({}),
        "queryStringParameters": None,
        "pathParameters": None,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "employee-user-id-5678",
                    "email": "employee@example.com",
                    "cognito:groups": "employee",
                }
            }
        },
    }


@pytest.fixture
def employee_event():
    """API Gateway proxy event with valid employee Cognito claims."""
    return {
        "httpMethod": "POST",
        "path": "/assets/my-assets",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({}),
        "queryStringParameters": None,
        "pathParameters": None,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "employee-user-id-9999",
                    "email": "jane.doe@example.com",
                    "cognito:groups": "employee",
                }
            }
        },
    }


# ---------------------------------------------------------------------------
# Helper fixtures — pre-seeded data for handover / assignment tests
# ---------------------------------------------------------------------------
@pytest.fixture
def in_stock_asset(aws_mocks):
    """Seed an IN_STOCK AssetMetadataModel item and return its asset_id."""
    table = aws_mocks["table"]
    asset_id = "test-asset-001"
    table.put_item(
        Item={
            "PK": f"ASSET#{asset_id}",
            "SK": "METADATA",
            "ProcurementID": "PROC-001",
            "ApprovedBudget": "5000",
            "Requestor": "admin-user-id-1234",
            "InvoiceNumber": "INV-001",
            "Vendor": "Dell",
            "PurchaseDate": "2024-06-01",
            "SerialNumber": "SN-12345",
            "Brand": "Dell",
            "Model": "Latitude 5540",
            "ProductDescription": "Business Laptop",
            "Cost": "4500",
            "PaymentMethod": "Corporate Card",
            "Status": "IN_STOCK",
            "Condition": "New",
            "EntityType": "ASSET",
            "CreatedAt": "2024-06-01T00:00:00+00:00",
            "StatusIndexPK": "STATUS#IN_STOCK",
            "StatusIndexSK": f"ASSET#{asset_id}",
            "SerialNumberIndexPK": "SERIAL#SN-12345",
            "SerialNumberIndexSK": "METADATA",
        }
    )
    return asset_id


@pytest.fixture
def active_employee(aws_mocks):
    """Seed an active UserMetadataModel item and return its user_id."""
    table = aws_mocks["table"]
    user_id = "employee-user-id-9999"
    table.put_item(
        Item={
            "PK": f"USER#{user_id}",
            "SK": "METADATA",
            "UserID": user_id,
            "Fullname": "Jane Doe",
            "Email": "jane.doe@example.com",
            "Role": "employee",
            "Status": "active",
            "CreatedAt": "2024-01-15T00:00:00+00:00",
            "EntityType": "USER",
        }
    )
    return user_id


@pytest.fixture
def handover_record(aws_mocks, in_stock_asset, active_employee):
    """Seed a HandoverRecordModel linking the in_stock_asset to the active_employee.

    Returns a dict with asset_id, employee_id, and the handover SK.
    """
    table = aws_mocks["table"]
    asset_id = in_stock_asset
    employee_id = active_employee
    assignment_date = "2024-07-01T10:00:00+00:00"
    sk = f"HANDOVER#{assignment_date}"

    table.put_item(
        Item={
            "PK": f"ASSET#{asset_id}",
            "SK": sk,
            "EmployeeID": employee_id,
            "EmployeeName": "Jane Doe",
            "EmployeeEmail": "jane.doe@example.com",
            "AssignedByID": "admin-user-id-1234",
            "AssignmentDate": assignment_date,
            "EmployeeAssetIndexPK": f"EMPLOYEE#{employee_id}",
            "EmployeeAssetIndexSK": f"ASSET#{assignment_date}",
        }
    )

    # Also update the asset record with GSI keys
    table.update_item(
        Key={"PK": f"ASSET#{asset_id}", "SK": "METADATA"},
        UpdateExpression="SET EmployeeAssetIndexPK = :pk, EmployeeAssetIndexSK = :sk",
        ExpressionAttributeValues={
            ":pk": f"EMPLOYEE#{employee_id}",
            ":sk": f"ASSET#{assignment_date}",
        },
    )

    return {
        "asset_id": asset_id,
        "employee_id": employee_id,
        "handover_sk": sk,
        "assignment_date": assignment_date,
    }


# ---------------------------------------------------------------------------
# Phase 4 — Issue Management helper fixtures
# ---------------------------------------------------------------------------
ISSUE_ASSET_ID = "issue-asset-001"
ISSUE_EMPLOYEE_ID = "employee-user-id-9999"
ISSUE_ADMIN_ID = "admin-user-id-1234"
ISSUE_ASSIGNMENT_DATE = "2024-07-01T10:00:00+00:00"


@pytest.fixture
def assigned_asset(aws_mocks):
    """Seed an ASSIGNED asset with a Handover_Record linking it to the employee.

    Returns a dict with asset_id, employee_id, and assignment_date.
    """
    table = aws_mocks["table"]
    asset_id = ISSUE_ASSET_ID
    employee_id = ISSUE_EMPLOYEE_ID

    # Asset in ASSIGNED status
    table.put_item(
        Item={
            "PK": f"ASSET#{asset_id}",
            "SK": "METADATA",
            "ProcurementID": "PROC-100",
            "ApprovedBudget": "3000",
            "Requestor": ISSUE_ADMIN_ID,
            "InvoiceNumber": "INV-100",
            "Vendor": "Lenovo",
            "PurchaseDate": "2024-05-01",
            "SerialNumber": "SN-ISSUE-001",
            "Brand": "Lenovo",
            "Model": "ThinkPad X1",
            "ProductDescription": "Business Laptop",
            "Cost": "2800",
            "PaymentMethod": "Corporate Card",
            "Status": "ASSIGNED",
            "Condition": "Good",
            "EntityType": "ASSET",
            "CreatedAt": "2024-05-01T00:00:00+00:00",
            "StatusIndexPK": "STATUS#ASSIGNED",
            "StatusIndexSK": f"ASSET#{asset_id}",
            "SerialNumberIndexPK": "SERIAL#SN-ISSUE-001",
            "SerialNumberIndexSK": "METADATA",
            "EmployeeAssetIndexPK": f"EMPLOYEE#{employee_id}",
            "EmployeeAssetIndexSK": f"ASSET#{ISSUE_ASSIGNMENT_DATE}",
        }
    )

    # Handover record linking asset to employee
    table.put_item(
        Item={
            "PK": f"ASSET#{asset_id}",
            "SK": f"HANDOVER#{ISSUE_ASSIGNMENT_DATE}",
            "EmployeeID": employee_id,
            "EmployeeName": "Jane Doe",
            "EmployeeEmail": "jane.doe@example.com",
            "AssignedByID": ISSUE_ADMIN_ID,
            "AssignmentDate": ISSUE_ASSIGNMENT_DATE,
            "EmployeeAssetIndexPK": f"EMPLOYEE#{employee_id}",
            "EmployeeAssetIndexSK": f"ASSET#{ISSUE_ASSIGNMENT_DATE}",
        }
    )

    return {
        "asset_id": asset_id,
        "employee_id": employee_id,
        "assignment_date": ISSUE_ASSIGNMENT_DATE,
    }


@pytest.fixture
def sample_issue(aws_mocks):
    """Factory fixture that creates an Issue_Record at a given lifecycle stage.

    Usage::

        issue = sample_issue("TROUBLESHOOTING", asset_id="issue-asset-001")
        issue = sample_issue("REPLACEMENT_REQUIRED", asset_id="issue-asset-001")

    Returns a dict with asset_id, timestamp (SK suffix), and the full item.
    """
    table = aws_mocks["table"]
    created_ts = "2024-08-01T12:00:00+00:00"

    def _create(status="TROUBLESHOOTING", asset_id=ISSUE_ASSET_ID, timestamp=None):
        ts = timestamp or created_ts
        sk = f"ISSUE#{ts}"

        item = {
            "PK": f"ASSET#{asset_id}",
            "SK": sk,
            "IssueDescription": "Screen flickering intermittently",
            "Status": status,
            "ReportedBy": ISSUE_EMPLOYEE_ID,
            "CreatedAt": ts,
        }

        # Populate fields based on lifecycle stage
        if status in (
            "TROUBLESHOOTING",
            "UNDER_REPAIR",
            "SEND_WARRANTY",
            "RESOLVED",
            "REPLACEMENT_REQUIRED",
            "REPLACEMENT_APPROVED",
            "REPLACEMENT_REJECTED",
        ):
            item["TriagedBy"] = ISSUE_ADMIN_ID
            item["TriagedAt"] = "2024-08-02T09:00:00+00:00"

        if status in ("UNDER_REPAIR", "SEND_WARRANTY", "RESOLVED"):
            item["ActionPath"] = "Option A (Repair)"
            item["ResolvedBy"] = ISSUE_ADMIN_ID
            item["ResolvedAt"] = "2024-08-03T10:00:00+00:00"

        if status == "SEND_WARRANTY":
            item["WarrantySentAt"] = "2024-08-04T11:00:00+00:00"

        if status == "RESOLVED":
            item["CompletedAt"] = "2024-08-05T14:00:00+00:00"

        if status in (
            "REPLACEMENT_REQUIRED",
            "REPLACEMENT_APPROVED",
            "REPLACEMENT_REJECTED",
        ):
            item["ActionPath"] = "Option B (Replacement Required)"
            item["ResolvedBy"] = ISSUE_ADMIN_ID
            item["ResolvedAt"] = "2024-08-03T10:00:00+00:00"
            item["ReplacementJustification"] = "Beyond economical repair"

        if status == "REPLACEMENT_REQUIRED":
            item["IssueStatusIndexPK"] = "ISSUE_STATUS#REPLACEMENT_REQUIRED"
            item["IssueStatusIndexSK"] = f"ISSUE#{ts}"

        if status == "REPLACEMENT_APPROVED":
            item["ManagementReviewedBy"] = "mgmt-user-id-001"
            item["ManagementReviewedAt"] = "2024-08-06T15:00:00+00:00"
            item["ManagementRemarks"] = "Approved for replacement"

        if status == "REPLACEMENT_REJECTED":
            item["ManagementReviewedBy"] = "mgmt-user-id-001"
            item["ManagementReviewedAt"] = "2024-08-06T15:00:00+00:00"
            item["ManagementRejectionReason"] = "Try repair first"

        table.put_item(Item=item)
        return {"asset_id": asset_id, "timestamp": ts, "item": item}

    return _create


# ---------------------------------------------------------------------------
# Phase 4 — Event builder fixtures with configurable path parameters
# ---------------------------------------------------------------------------
@pytest.fixture
def make_employee_event():
    """Build an API Gateway event for an employee with configurable path/body.

    Usage::

        event = make_employee_event(
            method="POST",
            path="/assets/{asset_id}/issues",
            path_params={"asset_id": "issue-asset-001"},
            body={"issue_description": "Screen broken"},
        )
    """

    def _build(method="POST", path="/assets", path_params=None, body=None):
        return {
            "httpMethod": method,
            "path": path,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body) if body else None,
            "queryStringParameters": None,
            "pathParameters": path_params,
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": ISSUE_EMPLOYEE_ID,
                        "email": "jane.doe@example.com",
                        "cognito:groups": "employee",
                    }
                }
            },
        }

    return _build


@pytest.fixture
def make_it_admin_event():
    """Build an API Gateway event for an IT admin with configurable path/body.

    Usage::

        event = make_it_admin_event(
            method="PUT",
            path="/assets/{asset_id}/issues/{timestamp}/triage",
            path_params={"asset_id": "issue-asset-001", "timestamp": "2024-08-01T12:00:00+00:00"},
        )
    """

    def _build(method="PUT", path="/assets", path_params=None, body=None):
        return {
            "httpMethod": method,
            "path": path,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body) if body else None,
            "queryStringParameters": None,
            "pathParameters": path_params,
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": ISSUE_ADMIN_ID,
                        "email": "admin@example.com",
                        "cognito:groups": "it-admin",
                    }
                }
            },
        }

    return _build


@pytest.fixture
def make_management_event():
    """Build an API Gateway event for a management user with configurable path/body.

    Usage::

        event = make_management_event(
            method="PUT",
            path="/assets/{asset_id}/issues/{timestamp}/management-review",
            path_params={"asset_id": "issue-asset-001", "timestamp": "2024-08-01T12:00:00+00:00"},
            body={"decision": "APPROVE", "remarks": "Looks good"},
        )
    """

    def _build(method="PUT", path="/assets", path_params=None, body=None):
        return {
            "httpMethod": method,
            "path": path,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body) if body else None,
            "queryStringParameters": None,
            "pathParameters": path_params,
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "mgmt-user-id-001",
                        "email": "manager@example.com",
                        "cognito:groups": "management",
                    }
                }
            },
        }

    return _build
