"""Counter stack — CounterProcessor (stream-triggered) + GetDashboardCounters."""

from aws_cdk import Stack, aws_iam as iam, aws_lambda as lambda_, aws_ssm as ssm
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)
from helpers.naming import get_resource_name, get_ssm_parameter_path


class CounterStack(Stack):
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

        # 1. CounterProcessor Lambda (stream-triggered)
        processor_fn = create_lambda_function(
            ctx,
            purpose="counter-processor",
            directory="CounterProcessor",
            construct_prefix="CounterProcessor",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:PutItem",
                    ],
                    [ctx.table_arn],
                ),
            ],
            timeout_seconds=60,
        )

        # DynamoDB Stream event source mapping
        lambda_.EventSourceMapping(
            self,
            "CounterProcessorStreamMapping",
            target=processor_fn,
            event_source_arn=stream_arn,
            starting_position=lambda_.StartingPosition.LATEST,
            batch_size=25,
            retry_attempts=3,
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

        # 2. GetDashboardCounters Lambda
        create_lambda_function(
            ctx,
            purpose="get-dashboard-counters",
            directory="GetDashboardCounters",
            construct_prefix="GetDashboardCounters",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem"],
                    [ctx.table_arn],
                ),
            ],
        )
