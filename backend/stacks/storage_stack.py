from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ssm as ssm,
)
from constructs import Construct

from helpers.naming import get_resource_name, get_ssm_parameter_path


class StorageStack(Stack):
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

        # ── S3 Bucket ──────────────────────────────────────────────
        # Note: Cannot use get_resource_name() here because self.account
        # is a CDK token — calling .lower() on it corrupts the token.
        # project_name and env_name are lowered explicitly; account resolves at deploy.
        bucket_name = f"{project_name.lower()}-{env_name.lower()}-assets-{self.account}"

        assets_bucket = s3.Bucket(
            self,
            "AssetsBucket",
            bucket_name=bucket_name,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.GET,
                    ],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    exposed_headers=[
                        "ETag",
                        "x-amz-request-id",
                        "x-amz-id-2",
                    ],
                )
            ],
            lifecycle_rules=[
                s3.LifecycleRule(
                    prefix="uploads/",
                    expiration=Duration.days(7),
                ),
            ],
        )

        # Grant Textract service read access to the bucket.
        # Textract calls HeadObject + GetObject internally when processing
        # async jobs (StartDocumentAnalysis). Without this, subsequent
        # Textract invocations intermittently fail with 403 on HeadObject.
        assets_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowTextractRead",
                actions=["s3:GetObject"],
                resources=[assets_bucket.arn_for_objects("*")],
                principals=[iam.ServicePrincipal("textract.amazonaws.com")],
                conditions={"StringEquals": {"aws:SourceAccount": self.account}},
            )
        )

        ssm.StringParameter(
            self,
            "AssetsBucketName",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "storage", "assets-bucket-name"
            ),
            string_value=assets_bucket.bucket_name,
        )

        # ── DynamoDB Table ─────────────────────────────────────────
        table_name = get_resource_name(project_name, env_name, "assets")

        assets_table = dynamodb.Table(
            self,
            "AssetsTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="TTL",
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # GSI1 — EntityTypeIndex
        assets_table.add_global_secondary_index(
            index_name="EntityTypeIndex",
            partition_key=dynamodb.Attribute(
                name="EntityType", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="CreatedAt", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI2 — StatusIndex
        assets_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(
                name="StatusIndexPK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="StatusIndexSK", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI3 — SerialNumberIndex
        assets_table.add_global_secondary_index(
            index_name="SerialNumberIndex",
            partition_key=dynamodb.Attribute(
                name="SerialNumberIndexPK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SerialNumberIndexSK", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI4 — EmployeeAssetIndex
        assets_table.add_global_secondary_index(
            index_name="EmployeeAssetIndex",
            partition_key=dynamodb.Attribute(
                name="EmployeeAssetIndexPK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="EmployeeAssetIndexSK", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI5 — SoftwareStatusIndex
        assets_table.add_global_secondary_index(
            index_name="SoftwareStatusIndex",
            partition_key=dynamodb.Attribute(
                name="SoftwareStatusIndexPK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SoftwareStatusIndexSK", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI6 — IssueStatusIndex
        assets_table.add_global_secondary_index(
            index_name="IssueStatusIndex",
            partition_key=dynamodb.Attribute(
                name="IssueStatusIndexPK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="IssueStatusIndexSK", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI7 — DisposalStatusIndex
        assets_table.add_global_secondary_index(
            index_name="DisposalStatusIndex",
            partition_key=dynamodb.Attribute(
                name="DisposalStatusIndexPK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="DisposalStatusIndexSK", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI8 — DisposalEntityIndex
        assets_table.add_global_secondary_index(
            index_name="DisposalEntityIndex",
            partition_key=dynamodb.Attribute(
                name="DisposalEntityType", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="InitiatedAt", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI9 — IssueEntityIndex
        assets_table.add_global_secondary_index(
            index_name="IssueEntityIndex",
            partition_key=dynamodb.Attribute(
                name="IssueEntityType", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="CreatedAt", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI10 — SoftwareEntityIndex
        assets_table.add_global_secondary_index(
            index_name="SoftwareEntityIndex",
            partition_key=dynamodb.Attribute(
                name="SoftwareEntityType", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="CreatedAt", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI11 — MaintenanceEntityIndex
        assets_table.add_global_secondary_index(
            index_name="MaintenanceEntityIndex",
            partition_key=dynamodb.Attribute(
                name="MaintenanceEntityType", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="MaintenanceTimestamp", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI12 — CategoryEntityIndex
        assets_table.add_global_secondary_index(
            index_name="CategoryEntityIndex",
            partition_key=dynamodb.Attribute(
                name="CategoryEntityType", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="CreatedAt", type=dynamodb.AttributeType.STRING
            ),
        )

        # GSI13 — CategoryNameIndex
        assets_table.add_global_secondary_index(
            index_name="CategoryNameIndex",
            partition_key=dynamodb.Attribute(
                name="CategoryNameIndexPK", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.KEYS_ONLY,
        )

        # GSI14 — ActivityEntityIndex
        assets_table.add_global_secondary_index(
            index_name="ActivityEntityIndex",
            partition_key=dynamodb.Attribute(
                name="ActivityEntityType", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="Timestamp", type=dynamodb.AttributeType.STRING
            ),
        )

        ssm.StringParameter(
            self,
            "AssetsTableName",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "storage", "assets-table-name"
            ),
            string_value=assets_table.table_name,
        )

        ssm.StringParameter(
            self,
            "AssetsTableStreamArn",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "storage", "assets-table-stream-arn"
            ),
            string_value=assets_table.table_stream_arn,
        )
