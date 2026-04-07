"""Maintenance stack — stream processor for MaintenanceEntityIndex GSI backfill."""

from aws_cdk import Stack, aws_iam as iam, aws_lambda as lambda_, aws_ssm as ssm
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)
from helpers.naming import get_resource_name, get_ssm_parameter_path


class MaintenanceStack(Stack):
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

        # SSM lookup for DynamoDB Stream ARN
        stream_arn = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "storage", "assets-table-stream-arn"
            ),
        )

        # 1. MaintenanceStreamProcessor (stream-triggered)
        processor_fn = create_lambda_function(
            ctx,
            purpose="maintenance-stream-processor",
            directory="MaintenanceStreamProcessor",
            construct_prefix="MaintenanceStreamProcessor",
            policies=[
                PolicyConfig(
                    ["dynamodb:UpdateItem"],
                    [ctx.table_arn],
                ),
            ],
            timeout_seconds=60,
        )

        # DynamoDB Stream event source mapping
        lambda_.EventSourceMapping(
            self,
            "MaintenanceStreamMapping",
            target=processor_fn,
            event_source_arn=stream_arn,
            starting_position=lambda_.StartingPosition.LATEST,
            batch_size=10,
        )

        # IAM permissions for stream read operations
        processor_fn.role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetRecords",
                    "dynamodb:GetShardIterator",
                    "dynamodb:DescribeStream",
                    "dynamodb:ListStreams",
                ],
                resources=[f"{ctx.table_arn}/stream/*"],
            )
        )
