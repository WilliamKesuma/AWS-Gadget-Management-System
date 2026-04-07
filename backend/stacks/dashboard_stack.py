"""Dashboard stack — role-specific stats, asset distribution, recent activity, approval hub."""

from aws_cdk import Stack
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)


class DashboardStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project_name: str,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ctx = LambdaStackContext(self, project_name, env_name)

        read_policy = PolicyConfig(
            ["dynamodb:GetItem", "dynamodb:Query"],
            [ctx.table_arn, ctx.table_gsi_arn],
        )
        get_only_policy = PolicyConfig(
            ["dynamodb:GetItem"],
            [ctx.table_arn],
        )
        batch_read_policy = PolicyConfig(
            ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchGetItem"],
            [ctx.table_arn, ctx.table_gsi_arn],
        )

        # IT Admin Stats — single GetItem on DASHBOARD_COUNTERS
        create_lambda_function(
            ctx,
            purpose="get-it-admin-stats",
            directory="GetITAdminStats",
            construct_prefix="GetITAdminStats",
            policies=[get_only_policy],
        )

        # Management Stats — single GetItem on DASHBOARD_COUNTERS
        create_lambda_function(
            ctx,
            purpose="get-management-stats",
            directory="GetManagementStats",
            construct_prefix="GetManagementStats",
            policies=[get_only_policy],
        )

        # Employee Stats — single GetItem on USER#<id> METADATA (counters maintained by stream)
        create_lambda_function(
            ctx,
            purpose="get-employee-stats",
            directory="GetEmployeeStats",
            construct_prefix="GetEmployeeStats",
            policies=[get_only_policy],
        )

        # Finance Stats — single GetItem on DASHBOARD_COUNTERS
        create_lambda_function(
            ctx,
            purpose="get-finance-stats",
            directory="GetFinanceStats",
            construct_prefix="GetFinanceStats",
            policies=[get_only_policy],
        )

        # Asset Distribution — single GetItem on DASHBOARD_COUNTERS
        create_lambda_function(
            ctx,
            purpose="get-asset-distribution",
            directory="GetAssetDistribution",
            construct_prefix="GetAssetDistribution",
            policies=[get_only_policy],
        )

        # Recent Activity — queries ActivityEntityIndex
        create_lambda_function(
            ctx,
            purpose="get-recent-activity",
            directory="GetRecentActivity",
            construct_prefix="GetRecentActivity",
            policies=[read_policy],
        )

        # Approval Hub — queries multiple GSIs + batch resolves user names
        create_lambda_function(
            ctx,
            purpose="get-approval-hub",
            directory="GetApprovalHub",
            construct_prefix="GetApprovalHub",
            policies=[batch_read_policy],
        )

        # Assets Page Stats — single GetItem on DASHBOARD_COUNTERS
        create_lambda_function(
            ctx,
            purpose="get-assets-page-stats",
            directory="GetAssetsPageStats",
            construct_prefix="GetAssetsPageStats",
            policies=[get_only_policy],
        )

        # Requests Page Stats (IT Admin/Management) — GetItem + live query for completed_today
        create_lambda_function(
            ctx,
            purpose="get-requests-it-admin-stats",
            directory="GetRequestsITAdminStats",
            construct_prefix="GetRequestsITAdminStats",
            policies=[read_policy],
        )

        # Requests Page Stats (Employee) — live queries scoped to caller
        create_lambda_function(
            ctx,
            purpose="get-requests-employee-stats",
            directory="GetRequestsEmployeeStats",
            construct_prefix="GetRequestsEmployeeStats",
            policies=[read_policy],
        )
