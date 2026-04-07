import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.types import TypeDeserializer

from utils.enums import (
    Activity_Type_Enum,
    Asset_Status_Enum,
    Issue_Status_Enum,
    Software_Status_Enum,
    Target_Type_Enum,
)

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
deserializer = TypeDeserializer()

# Map SK prefixes to their counter field names.
# Assets and Assignments are identified by PK + SK = METADATA patterns.
SK_PREFIX_TO_COUNTER = {
    "ISSUE#": "IssueCount",
    "RETURN#": "ReturnCount",
    "DISPOSAL#": "DisposalCount",
    "SOFTWARE#": "SoftwareRequestCount",
}

COUNTER_KEY = {"PK": "ENTITY_COUNTERS", "SK": "METADATA"}
DASHBOARD_KEY = {"PK": "DASHBOARD_COUNTERS", "SK": "METADATA"}

# Asset statuses excluded from total active assets
EXCLUDED_ASSET_STATUSES = {
    Asset_Status_Enum.DISPOSED,
    Asset_Status_Enum.ASSET_PENDING_APPROVAL,
    Asset_Status_Enum.ASSET_REJECTED,
}

# Asset statuses that count as "in maintenance"
MAINTENANCE_STATUSES = {
    Asset_Status_Enum.UNDER_REPAIR,
    Asset_Status_Enum.ISSUE_REPORTED,
    Asset_Status_Enum.REPAIR_REQUIRED,
}

# Issue statuses actionable by IT Admin (pending issues)
PENDING_ISSUE_STATUSES = {
    Issue_Status_Enum.TROUBLESHOOTING,
    Issue_Status_Enum.UNDER_REPAIR,
    Issue_Status_Enum.SEND_WARRANTY,
}

# Approval-related statuses for management pending_approvals
PENDING_APPROVAL_ASSET_STATUS = Asset_Status_Enum.ASSET_PENDING_APPROVAL
PENDING_APPROVAL_DISPOSAL_STATUS = Asset_Status_Enum.DISPOSAL_PENDING
REPLACEMENT_REQUIRED_STATUS = Issue_Status_Enum.REPLACEMENT_REQUIRED
ESCALATED_TO_MANAGEMENT_STATUS = Software_Status_Enum.ESCALATED_TO_MANAGEMENT

# Issue terminal statuses (for TotalActiveRequests)
ISSUE_TERMINAL_STATUSES = {
    Issue_Status_Enum.RESOLVED,
    Issue_Status_Enum.REPLACEMENT_APPROVED,
    Issue_Status_Enum.REPLACEMENT_REJECTED,
}

# Software terminal statuses (for TotalActiveRequests)
SOFTWARE_TERMINAL_STATUSES = {
    Software_Status_Enum.SOFTWARE_INSTALL_APPROVED,
    Software_Status_Enum.SOFTWARE_INSTALL_REJECTED,
}


def _employee_counter_key(employee_id: str) -> dict:
    """Return the DynamoDB key for an employee's USER metadata record."""
    return {"PK": f"USER#{employee_id}", "SK": "METADATA"}


def _deserialize_image(image: dict) -> dict:
    """Convert a DynamoDB JSON image to a plain Python dict."""
    return {k: deserializer.deserialize(v) for k, v in image.items()}


def _resolve_counter_field(pk: str, sk: str) -> str | None:
    """Determine which counter field a record maps to, or None to skip."""
    if pk.startswith("ASSET#") and sk == "METADATA":
        return "AssetCount"
    for prefix, field_name in SK_PREFIX_TO_COUNTER.items():
        if sk.startswith(prefix):
            return field_name
    return None


def _resolve_assignment_change(old_image: dict | None, new_image: dict | None) -> int:
    """Return +1, -1, or 0 for assignment counter based on status transitions."""
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")
    if old_status == new_status:
        return 0
    delta = 0
    if new_status == Asset_Status_Enum.ASSIGNED:
        delta += 1
    if old_status == Asset_Status_Enum.ASSIGNED:
        delta -= 1
    return delta


def _increment_counter(key: dict, field_name: str, delta: int) -> None:
    """Atomically increment (or decrement) a counter field."""
    if delta == 0:
        return
    table.update_item(
        Key=key,
        UpdateExpression="ADD #field :delta",
        ExpressionAttributeNames={"#field": field_name},
        ExpressionAttributeValues={":delta": delta},
    )


def _increment_counter_value(key: dict, field_name: str, delta) -> None:
    """Atomically increment a counter field by a Decimal/int value."""
    if not delta:
        return
    table.update_item(
        Key=key,
        UpdateExpression="ADD #field :delta",
        ExpressionAttributeNames={"#field": field_name},
        ExpressionAttributeValues={":delta": delta},
    )


def _update_category_count(category: str, delta: int) -> None:
    """Atomically update a category count in the DASHBOARD_COUNTERS map."""
    if delta == 0 or not category:
        return
    table.update_item(
        Key=DASHBOARD_KEY,
        UpdateExpression="ADD #cc.#cat :delta",
        ExpressionAttributeNames={"#cc": "CategoryCounts", "#cat": category},
        ExpressionAttributeValues={":delta": delta},
    )


def _handle_asset_metadata(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Handle dashboard counter updates for asset metadata changes."""
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")
    old_category = (old_image or {}).get("Category")
    new_category = (new_image or {}).get("Category")
    old_cost = (old_image or {}).get("Cost")
    new_cost = (new_image or {}).get("Cost")

    if event_name == "INSERT":
        if new_status and new_status not in EXCLUDED_ASSET_STATUSES:
            _increment_counter(DASHBOARD_KEY, "TotalActiveAssets", 1)
        if new_status in MAINTENANCE_STATUSES:
            _increment_counter(DASHBOARD_KEY, "InMaintenance", 1)
        if new_status == Asset_Status_Enum.IN_STOCK:
            _increment_counter(DASHBOARD_KEY, "InStock", 1)
        if new_status == Asset_Status_Enum.ASSIGNED:
            _increment_counter(DASHBOARD_KEY, "Assigned", 1)
        if new_status == Asset_Status_Enum.DISPOSED:
            _increment_counter(DASHBOARD_KEY, "TotalDisposed", 1)
        if new_status == PENDING_APPROVAL_ASSET_STATUS:
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", 1)
        if new_status == PENDING_APPROVAL_DISPOSAL_STATUS:
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", 1)
            _increment_counter(DASHBOARD_KEY, "ScheduledDisposals", 1)
        # Asset value
        if new_cost and new_status not in EXCLUDED_ASSET_STATUSES:
            _increment_counter_value(DASHBOARD_KEY, "TotalAssetValue", int(new_cost))
        # Category distribution
        if new_category and new_status not in EXCLUDED_ASSET_STATUSES:
            _update_category_count(new_category, 1)

    elif event_name == "REMOVE":
        if old_status and old_status not in EXCLUDED_ASSET_STATUSES:
            _increment_counter(DASHBOARD_KEY, "TotalActiveAssets", -1)
        if old_status in MAINTENANCE_STATUSES:
            _increment_counter(DASHBOARD_KEY, "InMaintenance", -1)
        if old_status == Asset_Status_Enum.IN_STOCK:
            _increment_counter(DASHBOARD_KEY, "InStock", -1)
        if old_status == Asset_Status_Enum.ASSIGNED:
            _increment_counter(DASHBOARD_KEY, "Assigned", -1)
        if old_status == Asset_Status_Enum.DISPOSED:
            _increment_counter(DASHBOARD_KEY, "TotalDisposed", -1)
        if old_status == PENDING_APPROVAL_ASSET_STATUS:
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", -1)
        if old_status == PENDING_APPROVAL_DISPOSAL_STATUS:
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", -1)
            _increment_counter(DASHBOARD_KEY, "ScheduledDisposals", -1)
        if old_cost and old_status not in EXCLUDED_ASSET_STATUSES:
            _increment_counter_value(DASHBOARD_KEY, "TotalAssetValue", -int(old_cost))
        if old_category and old_status not in EXCLUDED_ASSET_STATUSES:
            _update_category_count(old_category, -1)

    elif event_name == "MODIFY" and old_status != new_status:
        old_active = old_status not in EXCLUDED_ASSET_STATUSES if old_status else False
        new_active = new_status not in EXCLUDED_ASSET_STATUSES if new_status else False

        # TotalActiveAssets
        if not old_active and new_active:
            _increment_counter(DASHBOARD_KEY, "TotalActiveAssets", 1)
        elif old_active and not new_active:
            _increment_counter(DASHBOARD_KEY, "TotalActiveAssets", -1)

        # InMaintenance
        old_maint = old_status in MAINTENANCE_STATUSES
        new_maint = new_status in MAINTENANCE_STATUSES
        if not old_maint and new_maint:
            _increment_counter(DASHBOARD_KEY, "InMaintenance", 1)
        elif old_maint and not new_maint:
            _increment_counter(DASHBOARD_KEY, "InMaintenance", -1)

        # InStock
        if (
            old_status != Asset_Status_Enum.IN_STOCK
            and new_status == Asset_Status_Enum.IN_STOCK
        ):
            _increment_counter(DASHBOARD_KEY, "InStock", 1)
        elif (
            old_status == Asset_Status_Enum.IN_STOCK
            and new_status != Asset_Status_Enum.IN_STOCK
        ):
            _increment_counter(DASHBOARD_KEY, "InStock", -1)

        # Assigned
        if (
            old_status != Asset_Status_Enum.ASSIGNED
            and new_status == Asset_Status_Enum.ASSIGNED
        ):
            _increment_counter(DASHBOARD_KEY, "Assigned", 1)
        elif (
            old_status == Asset_Status_Enum.ASSIGNED
            and new_status != Asset_Status_Enum.ASSIGNED
        ):
            _increment_counter(DASHBOARD_KEY, "Assigned", -1)

        # TotalDisposed
        if (
            old_status != Asset_Status_Enum.DISPOSED
            and new_status == Asset_Status_Enum.DISPOSED
        ):
            _increment_counter(DASHBOARD_KEY, "TotalDisposed", 1)
        elif (
            old_status == Asset_Status_Enum.DISPOSED
            and new_status != Asset_Status_Enum.DISPOSED
        ):
            _increment_counter(DASHBOARD_KEY, "TotalDisposed", -1)

        # PendingApprovals — asset creation approval
        if (
            old_status != PENDING_APPROVAL_ASSET_STATUS
            and new_status == PENDING_APPROVAL_ASSET_STATUS
        ):
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", 1)
        elif (
            old_status == PENDING_APPROVAL_ASSET_STATUS
            and new_status != PENDING_APPROVAL_ASSET_STATUS
        ):
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", -1)

        # PendingApprovals + ScheduledDisposals — disposal pending
        if (
            old_status != PENDING_APPROVAL_DISPOSAL_STATUS
            and new_status == PENDING_APPROVAL_DISPOSAL_STATUS
        ):
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", 1)
            _increment_counter(DASHBOARD_KEY, "ScheduledDisposals", 1)
        elif (
            old_status == PENDING_APPROVAL_DISPOSAL_STATUS
            and new_status != PENDING_APPROVAL_DISPOSAL_STATUS
        ):
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", -1)
            # Only decrement ScheduledDisposals if NOT going to DISPOSED (disposal completed keeps it scheduled until done)
            if new_status != Asset_Status_Enum.DISPOSED:
                _increment_counter(DASHBOARD_KEY, "ScheduledDisposals", -1)

        # TotalAssetValue — track value entering/leaving active inventory
        cost = new_cost or old_cost
        if cost:
            cost_int = int(cost)
            if not old_active and new_active:
                _increment_counter_value(DASHBOARD_KEY, "TotalAssetValue", cost_int)
            elif old_active and not new_active:
                _increment_counter_value(DASHBOARD_KEY, "TotalAssetValue", -cost_int)

        # Category distribution — track category entering/leaving active
        cat = new_category or old_category
        if cat:
            if not old_active and new_active:
                _update_category_count(cat, 1)
            elif old_active and not new_active:
                _update_category_count(cat, -1)

    # Handle category change on MODIFY (regardless of status change)
    if event_name == "MODIFY" and old_category != new_category:
        is_active = new_status not in EXCLUDED_ASSET_STATUSES if new_status else False
        if is_active:
            if old_category:
                _update_category_count(old_category, -1)
            if new_category:
                _update_category_count(new_category, 1)

    # Handle cost change on MODIFY (same status, active asset)
    if event_name == "MODIFY" and old_status == new_status and old_cost != new_cost:
        is_active = new_status not in EXCLUDED_ASSET_STATUSES if new_status else False
        if is_active:
            delta = int(new_cost or 0) - int(old_cost or 0)
            if delta:
                _increment_counter_value(DASHBOARD_KEY, "TotalAssetValue", delta)


def _handle_issue_record(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Handle dashboard counter updates for issue record changes."""
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")

    if event_name == "INSERT":
        if new_status in PENDING_ISSUE_STATUSES:
            _increment_counter(DASHBOARD_KEY, "PendingIssues", 1)
        if new_status == REPLACEMENT_REQUIRED_STATUS:
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", 1)
        # TotalActiveRequests — non-terminal issues
        if new_status not in ISSUE_TERMINAL_STATUSES:
            _increment_counter(DASHBOARD_KEY, "TotalActiveRequests", 1)

    elif event_name == "REMOVE":
        if old_status in PENDING_ISSUE_STATUSES:
            _increment_counter(DASHBOARD_KEY, "PendingIssues", -1)
        if old_status == REPLACEMENT_REQUIRED_STATUS:
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", -1)
        if old_status not in ISSUE_TERMINAL_STATUSES:
            _increment_counter(DASHBOARD_KEY, "TotalActiveRequests", -1)

    elif event_name == "MODIFY" and old_status != new_status:
        old_pending = old_status in PENDING_ISSUE_STATUSES
        new_pending = new_status in PENDING_ISSUE_STATUSES
        if not old_pending and new_pending:
            _increment_counter(DASHBOARD_KEY, "PendingIssues", 1)
        elif old_pending and not new_pending:
            _increment_counter(DASHBOARD_KEY, "PendingIssues", -1)

        # Replacement required → management approval
        if (
            old_status != REPLACEMENT_REQUIRED_STATUS
            and new_status == REPLACEMENT_REQUIRED_STATUS
        ):
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", 1)
        elif (
            old_status == REPLACEMENT_REQUIRED_STATUS
            and new_status != REPLACEMENT_REQUIRED_STATUS
        ):
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", -1)

        # TotalActiveRequests — transition into/out of terminal
        old_terminal = old_status in ISSUE_TERMINAL_STATUSES
        new_terminal = new_status in ISSUE_TERMINAL_STATUSES
        if not old_terminal and new_terminal:
            _increment_counter(DASHBOARD_KEY, "TotalActiveRequests", -1)
        elif old_terminal and not new_terminal:
            _increment_counter(DASHBOARD_KEY, "TotalActiveRequests", 1)


def _handle_software_record(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Handle dashboard counter updates for software request changes."""
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")

    if event_name == "INSERT":
        if new_status == ESCALATED_TO_MANAGEMENT_STATUS:
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", 1)
        if new_status not in SOFTWARE_TERMINAL_STATUSES:
            _increment_counter(DASHBOARD_KEY, "TotalActiveRequests", 1)
    elif event_name == "REMOVE":
        if old_status == ESCALATED_TO_MANAGEMENT_STATUS:
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", -1)
        if old_status not in SOFTWARE_TERMINAL_STATUSES:
            _increment_counter(DASHBOARD_KEY, "TotalActiveRequests", -1)
    elif event_name == "MODIFY" and old_status != new_status:
        if (
            old_status != ESCALATED_TO_MANAGEMENT_STATUS
            and new_status == ESCALATED_TO_MANAGEMENT_STATUS
        ):
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", 1)
        elif (
            old_status == ESCALATED_TO_MANAGEMENT_STATUS
            and new_status != ESCALATED_TO_MANAGEMENT_STATUS
        ):
            _increment_counter(DASHBOARD_KEY, "PendingApprovals", -1)

        # TotalActiveRequests
        old_terminal = old_status in SOFTWARE_TERMINAL_STATUSES
        new_terminal = new_status in SOFTWARE_TERMINAL_STATUSES
        if not old_terminal and new_terminal:
            _increment_counter(DASHBOARD_KEY, "TotalActiveRequests", -1)
        elif old_terminal and not new_terminal:
            _increment_counter(DASHBOARD_KEY, "TotalActiveRequests", 1)


def _handle_return_record(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Handle dashboard counter updates for return record changes."""
    old_resolved = (old_image or {}).get("ResolvedStatus")
    new_resolved = (new_image or {}).get("ResolvedStatus")

    if event_name == "INSERT":
        # New return — pending if no ResolvedStatus
        if not new_resolved:
            _increment_counter(DASHBOARD_KEY, "PendingReturns", 1)
    elif event_name == "REMOVE":
        if not old_resolved:
            _increment_counter(DASHBOARD_KEY, "PendingReturns", -1)
    elif event_name == "MODIFY":
        # Transition from pending (no ResolvedStatus) to completed
        if not old_resolved and new_resolved:
            _increment_counter(DASHBOARD_KEY, "PendingReturns", -1)
        elif old_resolved and not new_resolved:
            _increment_counter(DASHBOARD_KEY, "PendingReturns", 1)


# ── Employee Per-User Counters ────────────────────────────────────────────
# Maintains AssignedAssets, PendingRequests, PendingSignatures on USER#<id> METADATA


def _handle_employee_asset_counters(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Update AssignedAssets counter on the employee's user record when asset status changes."""
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")
    if old_status == new_status:
        return

    # Determine the employee from EmployeeAssetIndexPK
    image = new_image or old_image or {}
    emp_pk = image.get("EmployeeAssetIndexPK", "")
    if not emp_pk:
        return
    employee_id = emp_pk.replace("EMPLOYEE#", "")
    if not employee_id:
        return

    key = _employee_counter_key(employee_id)

    if (
        old_status != Asset_Status_Enum.ASSIGNED
        and new_status == Asset_Status_Enum.ASSIGNED
    ):
        _increment_counter(key, "AssignedAssets", 1)
    elif (
        old_status == Asset_Status_Enum.ASSIGNED
        and new_status != Asset_Status_Enum.ASSIGNED
    ):
        _increment_counter(key, "AssignedAssets", -1)


def _handle_employee_issue_counters(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Update PendingRequests counter when issue status changes for the reporting employee."""
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")
    employee_id = (new_image or old_image or {}).get("ReportedBy")
    if not employee_id:
        return

    key = _employee_counter_key(employee_id)

    if event_name == "INSERT":
        if new_status and new_status not in ISSUE_TERMINAL_STATUSES:
            _increment_counter(key, "PendingRequests", 1)
    elif event_name == "REMOVE":
        if old_status and old_status not in ISSUE_TERMINAL_STATUSES:
            _increment_counter(key, "PendingRequests", -1)
    elif event_name == "MODIFY" and old_status != new_status:
        old_terminal = old_status in ISSUE_TERMINAL_STATUSES
        new_terminal = new_status in ISSUE_TERMINAL_STATUSES
        if not old_terminal and new_terminal:
            _increment_counter(key, "PendingRequests", -1)
        elif old_terminal and not new_terminal:
            _increment_counter(key, "PendingRequests", 1)


def _handle_employee_software_counters(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Update PendingRequests counter when software request status changes."""
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")
    employee_id = (new_image or old_image or {}).get("RequestedBy")
    if not employee_id:
        return

    key = _employee_counter_key(employee_id)

    if event_name == "INSERT":
        if new_status and new_status not in SOFTWARE_TERMINAL_STATUSES:
            _increment_counter(key, "PendingRequests", 1)
    elif event_name == "REMOVE":
        if old_status and old_status not in SOFTWARE_TERMINAL_STATUSES:
            _increment_counter(key, "PendingRequests", -1)
    elif event_name == "MODIFY" and old_status != new_status:
        old_terminal = old_status in SOFTWARE_TERMINAL_STATUSES
        new_terminal = new_status in SOFTWARE_TERMINAL_STATUSES
        if not old_terminal and new_terminal:
            _increment_counter(key, "PendingRequests", -1)
        elif old_terminal and not new_terminal:
            _increment_counter(key, "PendingRequests", 1)


def _handle_employee_handover_counters(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Update PendingSignatures counter when handover records are created or accepted."""
    image = new_image or old_image or {}
    employee_id = image.get("EmployeeID")
    if not employee_id:
        return

    key = _employee_counter_key(employee_id)

    if event_name == "INSERT":
        # New handover without AcceptedAt → pending signature
        if not (new_image or {}).get("AcceptedAt"):
            _increment_counter(key, "PendingSignatures", 1)
    elif event_name == "MODIFY":
        old_accepted = (old_image or {}).get("AcceptedAt")
        new_accepted = (new_image or {}).get("AcceptedAt")
        if new_accepted and not old_accepted:
            _increment_counter(key, "PendingSignatures", -1)


def _handle_employee_return_counters(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Update PendingSignatures counter when return records need employee signature.

    Return records don't store the employee ID directly. We look up the asset's
    EmployeeAssetIndexPK to find the assigned employee.
    """
    image = new_image or old_image or {}
    pk = image.get("PK", "")
    if not pk.startswith("ASSET#"):
        return

    asset_id = pk.replace("ASSET#", "")

    if event_name == "INSERT":
        # New return without UserSignatureS3Key → pending signature
        if not (new_image or {}).get("UserSignatureS3Key"):
            # Look up the employee from the asset record
            asset_item = table.get_item(
                Key={"PK": f"ASSET#{asset_id}", "SK": "METADATA"},
                ProjectionExpression="EmployeeAssetIndexPK",
            ).get("Item")
            if asset_item:
                emp_pk = asset_item.get("EmployeeAssetIndexPK", "")
                employee_id = emp_pk.replace("EMPLOYEE#", "") if emp_pk else ""
                if employee_id:
                    _increment_counter(
                        _employee_counter_key(employee_id), "PendingSignatures", 1
                    )
    elif event_name == "MODIFY":
        old_sig = (old_image or {}).get("UserSignatureS3Key")
        new_sig = (new_image or {}).get("UserSignatureS3Key")
        if new_sig and not old_sig:
            # Completed by employee — CompletedBy field has the employee ID
            employee_id = (new_image or {}).get("CompletedBy", "")
            if employee_id:
                _increment_counter(
                    _employee_counter_key(employee_id), "PendingSignatures", -1
                )


# ── Activity Record Helpers ──────────────────────────────────────────────

# Cache resolved user names within a single invocation
_user_cache: dict[str, tuple[str, str]] = {}


def _resolve_actor(actor_id: str) -> tuple[str, str]:
    """Resolve a user ID to (fullname, role). Returns (actor_id, 'unknown') on miss."""
    if not actor_id:
        return ("Unknown", "unknown")
    if actor_id in _user_cache:
        return _user_cache[actor_id]
    try:
        item = table.get_item(
            Key={"PK": f"USER#{actor_id}", "SK": "METADATA"},
            ProjectionExpression="Fullname, #r",
            ExpressionAttributeNames={"#r": "Role"},
        ).get("Item")
        if item:
            result = (item.get("Fullname", actor_id), item.get("Role", "unknown"))
        else:
            result = (actor_id, "unknown")
    except Exception:
        result = (actor_id, "unknown")
    _user_cache[actor_id] = result
    return result


def _write_activity(
    activity: str,
    activity_type: str,
    actor_id: str,
    target_id: str,
    target_type: str,
    timestamp: str,
) -> None:
    """Write an activity record to DynamoDB for the recent activity feed."""
    actor_name, actor_role = _resolve_actor(actor_id)
    activity_id = str(uuid.uuid4())
    item = {
        "PK": f"ACTIVITY#{activity_id}",
        "SK": "METADATA",
        "ActivityID": activity_id,
        "Activity": activity,
        "ActivityType": activity_type,
        "ActorID": actor_id or "system",
        "ActorName": actor_name,
        "ActorRole": actor_role,
        "TargetID": target_id,
        "TargetType": target_type,
        "Timestamp": timestamp,
        "ActivityEntityType": "ACTIVITY",
    }
    table.put_item(Item=item)


def _emit_asset_activity(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Emit activity records for asset metadata changes."""
    image = new_image or old_image or {}
    asset_id = image.get("PK", "").replace("ASSET#", "")
    timestamp = image.get("CreatedAt", datetime.now(timezone.utc).isoformat())
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")

    if event_name == "INSERT":
        _write_activity(
            activity=f"Created new asset {asset_id}",
            activity_type=Activity_Type_Enum.ASSET_CREATION,
            actor_id="",
            target_id=asset_id,
            target_type=Target_Type_Enum.ASSET,
            timestamp=timestamp,
        )
    elif event_name == "MODIFY" and old_status != new_status:
        # Assignment is handled by _emit_handover_activity (HANDOVER# INSERT has actor info)
        if new_status == Asset_Status_Enum.DISPOSED:
            _write_activity(
                activity=f"Completed disposal of asset {asset_id}",
                activity_type=Activity_Type_Enum.DISPOSAL,
                actor_id="",
                target_id=asset_id,
                target_type=Target_Type_Enum.ASSET,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        elif (
            old_status == Asset_Status_Enum.ASSET_PENDING_APPROVAL
            and new_status not in (Asset_Status_Enum.ASSET_PENDING_APPROVAL,)
        ):
            action = (
                "Approved"
                if new_status != Asset_Status_Enum.ASSET_REJECTED
                else "Rejected"
            )
            _write_activity(
                activity=f"{action} asset creation for {asset_id}",
                activity_type=Activity_Type_Enum.APPROVAL,
                actor_id="",
                target_id=asset_id,
                target_type=Target_Type_Enum.ASSET,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )


def _emit_issue_activity(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Emit activity records for issue record changes."""
    image = new_image or old_image or {}
    asset_id = image.get("PK", "").replace("ASSET#", "")
    issue_id = image.get("IssueID", image.get("SK", "").replace("ISSUE#", ""))
    timestamp = image.get("CreatedAt", datetime.now(timezone.utc).isoformat())
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")

    if event_name == "INSERT":
        actor_id = image.get("ReportedBy", "")
        _write_activity(
            activity=f"Reported issue on asset {asset_id}",
            activity_type=Activity_Type_Enum.ISSUE,
            actor_id=actor_id,
            target_id=issue_id,
            target_type=Target_Type_Enum.ISSUE,
            timestamp=timestamp,
        )
    elif event_name == "MODIFY" and old_status != new_status:
        actor_id = (
            image.get("ResolvedBy")
            or image.get("ManagementReviewedBy")
            or image.get("ReportedBy", "")
        )
        _write_activity(
            activity=f"Issue status changed to {new_status} for asset {asset_id}",
            activity_type=Activity_Type_Enum.ISSUE,
            actor_id=actor_id,
            target_id=issue_id,
            target_type=Target_Type_Enum.ISSUE,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


def _emit_software_activity(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Emit activity records for software request changes."""
    image = new_image or old_image or {}
    sw_id = image.get("SoftwareRequestID", image.get("SK", "").replace("SOFTWARE#", ""))
    sw_name = image.get("SoftwareName", "")
    timestamp = image.get("CreatedAt", datetime.now(timezone.utc).isoformat())
    old_status = (old_image or {}).get("Status")
    new_status = (new_image or {}).get("Status")

    if event_name == "INSERT":
        actor_id = image.get("RequestedBy", "")
        _write_activity(
            activity=f"Requested software installation: {sw_name}",
            activity_type=Activity_Type_Enum.SOFTWARE_REQUEST,
            actor_id=actor_id,
            target_id=sw_id,
            target_type=Target_Type_Enum.SOFTWARE,
            timestamp=timestamp,
        )
    elif event_name == "MODIFY" and old_status != new_status:
        actor_id = (
            image.get("ReviewedBy")
            or image.get("ManagementReviewedBy")
            or image.get("RequestedBy", "")
        )
        _write_activity(
            activity=f"Software request '{sw_name}' status changed to {new_status}",
            activity_type=Activity_Type_Enum.SOFTWARE_REQUEST,
            actor_id=actor_id,
            target_id=sw_id,
            target_type=Target_Type_Enum.SOFTWARE,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


def _emit_disposal_activity(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Emit activity records for disposal record changes."""
    image = new_image or old_image or {}
    asset_id = image.get("PK", "").replace("ASSET#", "")
    disposal_id = image.get("DisposalID", image.get("SK", "").replace("DISPOSAL#", ""))
    timestamp = image.get("InitiatedAt", datetime.now(timezone.utc).isoformat())

    if event_name == "INSERT":
        actor_id = image.get("InitiatedBy", "")
        _write_activity(
            activity=f"Initiated disposal for asset {asset_id}",
            activity_type=Activity_Type_Enum.DISPOSAL,
            actor_id=actor_id,
            target_id=disposal_id,
            target_type=Target_Type_Enum.DISPOSAL,
            timestamp=timestamp,
        )


def _emit_return_activity(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Emit activity records for return record changes."""
    image = new_image or old_image or {}
    asset_id = image.get("PK", "").replace("ASSET#", "")
    return_id = image.get("ReturnID", image.get("SK", "").replace("RETURN#", ""))
    timestamp = image.get("InitiatedAt", datetime.now(timezone.utc).isoformat())

    if event_name == "INSERT":
        actor_id = image.get("InitiatedBy", "")
        _write_activity(
            activity=f"Initiated return for asset {asset_id}",
            activity_type=Activity_Type_Enum.RETURN,
            actor_id=actor_id,
            target_id=return_id,
            target_type=Target_Type_Enum.RETURN,
            timestamp=timestamp,
        )
    elif event_name == "MODIFY":
        completed_at = (new_image or {}).get("CompletedAt")
        old_completed = (old_image or {}).get("CompletedAt")
        if completed_at and not old_completed:
            actor_id = (new_image or {}).get("CompletedBy", "")
            _write_activity(
                activity=f"Completed return for asset {asset_id}",
                activity_type=Activity_Type_Enum.RETURN,
                actor_id=actor_id,
                target_id=return_id,
                target_type=Target_Type_Enum.RETURN,
                timestamp=completed_at,
            )


def _emit_handover_activity(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Emit activity records for handover creation and acceptance."""
    image = new_image or old_image or {}
    asset_id = image.get("PK", "").replace("ASSET#", "")

    if event_name == "INSERT":
        # Assignment created — handover record has the actor and employee info
        actor_id = image.get("AssignedByID", "")
        employee_name = image.get("EmployeeName", "employee")
        timestamp = image.get("AssignmentDate", datetime.now(timezone.utc).isoformat())
        _write_activity(
            activity=f"Assigned asset {asset_id} to {employee_name}",
            activity_type=Activity_Type_Enum.ASSIGNMENT,
            actor_id=actor_id,
            target_id=asset_id,
            target_type=Target_Type_Enum.ASSET,
            timestamp=timestamp,
        )
    elif event_name == "MODIFY":
        old_accepted = (old_image or {}).get("AcceptedAt")
        new_accepted = (new_image or {}).get("AcceptedAt")
        if new_accepted and not old_accepted:
            actor_id = image.get("EmployeeID", "")
            _write_activity(
                activity=f"Accepted handover for asset {asset_id}",
                activity_type=Activity_Type_Enum.HANDOVER,
                actor_id=actor_id,
                target_id=asset_id,
                target_type=Target_Type_Enum.ASSET,
                timestamp=new_accepted,
            )


def _emit_user_activity(
    event_name: str, old_image: dict | None, new_image: dict | None
) -> None:
    """Emit activity records for user creation."""
    if event_name != "INSERT":
        return
    image = new_image or {}
    user_id = image.get("UserID", image.get("PK", "").replace("USER#", ""))
    fullname = image.get("Fullname", user_id)
    timestamp = image.get("CreatedAt", datetime.now(timezone.utc).isoformat())
    _write_activity(
        activity=f"Created user account for {fullname}",
        activity_type=Activity_Type_Enum.USER_CREATION,
        actor_id="",
        target_id=user_id,
        target_type=Target_Type_Enum.USER,
        timestamp=timestamp,
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    """Process DynamoDB Stream events and update entity + dashboard counters + activity feed."""
    records = event.get("Records", [])
    logger.info("Processing stream batch", record_count=len(records))

    # Clear user cache per invocation
    _user_cache.clear()

    for record in records:
        try:
            event_name = record.get("eventName", "")
            dynamodb_record = record.get("dynamodb", {})

            raw_new = dynamodb_record.get("NewImage")
            raw_old = dynamodb_record.get("OldImage")

            new_image = _deserialize_image(raw_new) if raw_new else None
            old_image = _deserialize_image(raw_old) if raw_old else None

            image = new_image or old_image
            if not image:
                continue

            pk = image.get("PK", "")
            sk = image.get("SK", "")

            # Skip activity records, counter records, and other non-entity records
            if pk.startswith("ACTIVITY#") or pk in (
                "ENTITY_COUNTERS",
                "DASHBOARD_COUNTERS",
            ):
                continue

            # ── Entity Counters ──
            counter_field = _resolve_counter_field(pk, sk)
            if counter_field:
                if event_name == "INSERT":
                    _increment_counter(COUNTER_KEY, counter_field, 1)
                elif event_name == "REMOVE":
                    _increment_counter(COUNTER_KEY, counter_field, -1)

                # Assignment counter on MODIFY
                if pk.startswith("ASSET#") and sk == "METADATA":
                    if event_name == "MODIFY":
                        delta = _resolve_assignment_change(old_image, new_image)
                        _increment_counter(COUNTER_KEY, "AssignmentCount", delta)
                    elif (
                        event_name == "INSERT"
                        and (new_image or {}).get("Status")
                        == Asset_Status_Enum.ASSIGNED
                    ):
                        _increment_counter(COUNTER_KEY, "AssignmentCount", 1)

            # ── Dashboard Counters ──
            if pk.startswith("ASSET#") and sk == "METADATA":
                _handle_asset_metadata(event_name, old_image, new_image)
                _handle_employee_asset_counters(event_name, old_image, new_image)
            elif sk.startswith("ISSUE#"):
                _handle_issue_record(event_name, old_image, new_image)
                _handle_employee_issue_counters(event_name, old_image, new_image)
            elif sk.startswith("SOFTWARE#"):
                _handle_software_record(event_name, old_image, new_image)
                _handle_employee_software_counters(event_name, old_image, new_image)
            elif sk.startswith("RETURN#"):
                _handle_return_record(event_name, old_image, new_image)
                _handle_employee_return_counters(event_name, old_image, new_image)
            elif sk.startswith("HANDOVER#"):
                _handle_employee_handover_counters(event_name, old_image, new_image)

            # ── Activity Feed ──
            try:
                if pk.startswith("ASSET#") and sk == "METADATA":
                    _emit_asset_activity(event_name, old_image, new_image)
                elif sk.startswith("ISSUE#"):
                    _emit_issue_activity(event_name, old_image, new_image)
                elif sk.startswith("SOFTWARE#"):
                    _emit_software_activity(event_name, old_image, new_image)
                elif sk.startswith("DISPOSAL#"):
                    _emit_disposal_activity(event_name, old_image, new_image)
                elif sk.startswith("RETURN#"):
                    _emit_return_activity(event_name, old_image, new_image)
                elif sk.startswith("HANDOVER#"):
                    _emit_handover_activity(event_name, old_image, new_image)
                elif pk.startswith("USER#") and sk == "METADATA":
                    _emit_user_activity(event_name, old_image, new_image)
            except Exception:
                logger.exception("Failed to emit activity record — non-fatal")

        except Exception:
            logger.exception("Error processing stream record", record=record)
            continue
