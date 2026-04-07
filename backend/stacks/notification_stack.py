"""Notification stack — NotificationProcessor, ListMyNotifications, MarkNotificationRead."""

from aws_cdk import Stack, aws_iam as iam, aws_lambda as lambda_, aws_ssm as ssm
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)
from helpers.naming import get_resource_name, get_ssm_parameter_path


class NotificationStack(Stack):
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

        # SSM lookups for WebSocket resources
        ws_connections_table_name = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "websocket", "connections-table-name"
            ),
        )
        ws_connections_table_arn = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "websocket", "connections-table-arn"
            ),
        )
        ws_endpoint = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(project_name, env_name, "websocket", "endpoint"),
        )
        ws_api_id = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(project_name, env_name, "websocket", "api-id"),
        )

        # 1. NotificationProcessor Lambda (stream-triggered)
        processor_fn = create_lambda_function(
            ctx,
            purpose="notification-processor",
            directory="NotificationProcessor",
            construct_prefix="NotificationProcessor",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:Query",
                        "dynamodb:BatchWriteItem",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:DeleteItem"],
                    [
                        ws_connections_table_arn,
                        f"{ws_connections_table_arn}/index/*",
                    ],
                ),
                PolicyConfig(
                    ["execute-api:ManageConnections"],
                    [f"arn:aws:execute-api:{self.region}:{self.account}:{ws_api_id}/*"],
                ),
            ],
            timeout_seconds=60,
        )

        # Add WebSocket environment variables to the processor
        processor_fn.add_environment("CONNECTIONS_TABLE", ws_connections_table_name)
        processor_fn.add_environment("WS_ENDPOINT", ws_endpoint)

        # DynamoDB Stream event source mapping
        lambda_.EventSourceMapping(
            self,
            "NotificationProcessorStreamMapping",
            target=processor_fn,
            event_source_arn=stream_arn,
            starting_position=lambda_.StartingPosition.LATEST,
            batch_size=10,
        )

        # IAM permissions for stream operations
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

        # 2. ListMyNotifications Lambda
        create_lambda_function(
            ctx,
            purpose="list-my-notifications",
            directory="ListMyNotifications",
            construct_prefix="ListMyNotifications",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 3. MarkNotificationRead Lambda
        create_lambda_function(
            ctx,
            purpose="mark-notification-read",
            directory="MarkNotificationRead",
            construct_prefix="MarkNotificationRead",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:UpdateItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
