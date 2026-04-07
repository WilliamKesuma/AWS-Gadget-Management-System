"""Scan feature stack — ScanWorker, ScanResultProcessor, GetScanResults Lambdas."""

from aws_cdk import Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda_event_sources as lambda_event_sources
from aws_cdk import aws_sns as sns
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_docker_lambda_function,
    create_lambda_function,
)
from helpers.naming import get_resource_name, get_ssm_parameter_path


class ScanStack(Stack):
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

        # ── SNS Topic for Textract async notifications ────────────
        textract_topic = sns.Topic(
            self,
            "TextractNotificationTopic",
            topic_name=get_resource_name(
                project_name, env_name, "textract-notifications"
            ),
        )

        # IAM Role for Textract to publish to SNS
        textract_sns_role = iam.Role(
            self,
            "TextractSNSRole",
            role_name=get_resource_name(project_name, env_name, "textract-sns-role"),
            assumed_by=iam.ServicePrincipal("textract.amazonaws.com"),
        )
        textract_sns_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=[textract_topic.topic_arn],
            )
        )

        # Export SNS topic ARN and role ARN to SSM for cross-stack consumers
        ssm.StringParameter(
            self,
            "TextractSNSTopicArnParam",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "scan", "textract-sns-topic-arn"
            ),
            string_value=textract_topic.topic_arn,
        )

        ssm.StringParameter(
            self,
            "TextractSNSRoleArnParam",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "scan", "textract-sns-role-arn"
            ),
            string_value=textract_sns_role.role_arn,
        )

        # ── ScanWorker Lambda ─────────────────────────────────────
        scan_worker_fn = create_docker_lambda_function(
            ctx,
            purpose="scan-worker",
            directory="ScanWorker",
            construct_prefix="ScanWorker",
            dockerfile_dir="services/lambdas/docker/scan",
            timeout_seconds=300,
            memory_size=512,
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:UpdateItem"], [ctx.table_arn]
                ),
                PolicyConfig(
                    ["s3:GetObject"], [ctx.bucket_arn, ctx.bucket_objects_arn]
                ),
                PolicyConfig(["s3:ListBucket"], [ctx.bucket_arn]),
                PolicyConfig(
                    [
                        "textract:AnalyzeDocument",
                        "textract:StartDocumentAnalysis",
                    ]
                ),
            ],
        )
        scan_worker_fn.add_environment(
            "TEXTRACT_SNS_TOPIC_ARN", textract_topic.topic_arn
        )
        scan_worker_fn.add_environment(
            "TEXTRACT_SNS_ROLE_ARN", textract_sns_role.role_arn
        )

        # ── ScanResultProcessor Lambda ────────────────────────────
        scan_result_processor_fn = create_lambda_function(
            ctx,
            purpose="scan-result-processor",
            directory="ScanResultProcessor",
            construct_prefix="ScanResultProcessor",
            timeout_seconds=60,
            policies=[
                PolicyConfig(["dynamodb:UpdateItem"], [ctx.table_arn]),
                PolicyConfig(["textract:GetDocumentAnalysis"]),
            ],
        )
        # SNS trigger — Textract publishes completion events here
        scan_result_processor_fn.add_event_source(
            lambda_event_sources.SnsEventSource(textract_topic)
        )

        # ── GetScanResults Lambda ─────────────────────────────────
        create_lambda_function(
            ctx,
            purpose="get-scan-result",
            directory="GetScanResults",
            construct_prefix="GetScanResults",
            policies=[
                PolicyConfig(["dynamodb:GetItem"], [ctx.table_arn]),
            ],
        )
