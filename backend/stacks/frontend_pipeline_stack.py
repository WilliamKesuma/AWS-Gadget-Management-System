from aws_cdk import Fn, RemovalPolicy, Stack, CfnOutput
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from helpers.naming import get_resource_name, get_ssm_parameter_path


class FrontendPipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project_name: str,
        env_name: str,
        repo_name: str = "Gadget_Management_System-Frontend",
        branch_name: str = "main",
        certificate_arn: str | None = None,
        domain_name: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        p, e = project_name, env_name

        def ssm_lookup(category: str, name: str) -> str:
            return ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name=get_ssm_parameter_path(p, e, category, name),
            )

        # -- Look up resource identifiers from SSM --------------------------
        rest_api_id = ssm_lookup("api", "rest-api-id")
        ws_api_id = ssm_lookup("websocket", "api-id")
        user_pool_id = ssm_lookup("auth", "user-pool-id")
        app_client_id = ssm_lookup("auth", "app-client-id")

        # -- S3 bucket for frontend hosting ----------------------------------
        frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=get_resource_name(p, e, "frontend"),
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # -- CloudFront distribution -----------------------------------------
        # Attach custom domain + certificate when provided
        custom_domain_kwargs = {}
        if certificate_arn and domain_name:
            custom_domain_kwargs = {
                "certificate": acm.Certificate.from_certificate_arn(
                    self, "SiteCertificate", certificate_arn
                ),
                "domain_names": [domain_name],
            }

        distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    frontend_bucket,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="/index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
            ],
            **custom_domain_kwargs,
        )

        # -- CodeCommit repo (import existing) -------------------------------
        repo = codecommit.Repository.from_repository_name(
            self,
            "FrontendRepo",
            repo_name,
        )

        # -- Build environment variables (SSM tokens resolve at deploy time) -
        vite_api_url = Fn.join(
            "",
            [
                "https://",
                rest_api_id,
                f".execute-api.{self.region}.amazonaws.com/{e}",
            ],
        )

        vite_ws_notification_url = Fn.join(
            "",
            [
                "wss://",
                ws_api_id,
                f".execute-api.{self.region}.amazonaws.com/{e}",
            ],
        )

        # -- CodeBuild project ----------------------------------------------
        build_project = codebuild.PipelineProject(
            self,
            "FrontendBuild",
            project_name=get_resource_name(p, e, "frontend", "build"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxArmBuildImage.AMAZON_LINUX_2023_STANDARD_3_0,
            ),
            environment_variables={
                "VITE_API_URL": codebuild.BuildEnvironmentVariable(
                    value=vite_api_url,
                ),
                "VITE_COGNITO_USER_POOL_ID": codebuild.BuildEnvironmentVariable(
                    value=user_pool_id,
                ),
                "VITE_COGNITO_APP_CLIENT_ID": codebuild.BuildEnvironmentVariable(
                    value=app_client_id,
                ),
                "VITE_AWS_REGION": codebuild.BuildEnvironmentVariable(
                    value=self.region,
                ),
                "VITE_WS_ENDPOINT": codebuild.BuildEnvironmentVariable(
                    value=vite_ws_notification_url
                ),
            },
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "install": {
                            "runtime-versions": {"nodejs": "24"},
                        },
                        "pre_build": {
                            "commands": [
                                'echo "VITE_API_URL=${VITE_API_URL}" > .env',
                                'echo "VITE_COGNITO_USER_POOL_ID=${VITE_COGNITO_USER_POOL_ID}" >> .env',
                                'echo "VITE_COGNITO_APP_CLIENT_ID=${VITE_COGNITO_APP_CLIENT_ID}" >> .env',
                                'echo "VITE_AWS_REGION=${VITE_AWS_REGION}" >> .env',
                                'echo "VITE_WS_ENDPOINT=${VITE_WS_ENDPOINT}" >> .env',
                                "npm install",
                            ]
                        },
                        "build": {"commands": ["npm run build"]},
                        "post_build": {
                            "commands": [
                                'echo "Build complete"',
                            ]
                        },
                    },
                    "artifacts": {
                        "base-directory": "dist",
                        "files": ["**/*"],
                    },
                }
            ),
        )

        # -- Invalidation CodeBuild project (runs after S3 deploy) -----------
        invalidation_project = codebuild.PipelineProject(
            self,
            "FrontendInvalidation",
            project_name=get_resource_name(p, e, "frontend", "invalidation"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxArmBuildImage.AMAZON_LINUX_2023_STANDARD_3_0,
            ),
            environment_variables={
                "DISTRIBUTION_ID": codebuild.BuildEnvironmentVariable(
                    value=distribution.distribution_id,
                ),
            },
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "build": {
                            "commands": [
                                'aws cloudfront create-invalidation --distribution-id ${DISTRIBUTION_ID} --paths "/*"',
                            ]
                        },
                    },
                }
            ),
        )

        distribution.grant_create_invalidation(invalidation_project)

        # Grant CodeBuild permission to invalidate CloudFront
        distribution.grant_create_invalidation(build_project)

        # Grant CodeBuild permission to write CloudWatch logs
        build_project.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/codebuild/{build_project.project_name}",
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/codebuild/{build_project.project_name}:*",
                ],
            )
        )

        # -- Pipeline --------------------------------------------------------
        source_output = codepipeline.Artifact("SourceOutput")
        build_output = codepipeline.Artifact("BuildOutput")

        pipeline = codepipeline.Pipeline(
            self,
            "FrontendPipeline",
            pipeline_name=get_resource_name(p, e, "frontend", "pipeline"),
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        codepipeline_actions.CodeCommitSourceAction(
                            action_name="CodeCommit",
                            repository=repo,
                            branch=branch_name,
                            output=source_output,
                        ),
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="Build",
                            project=build_project,
                            input=source_output,
                            outputs=[build_output],
                        ),
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="Deploy",
                    actions=[
                        codepipeline_actions.S3DeployAction(
                            action_name="DeployToS3",
                            bucket=frontend_bucket,
                            input=build_output,
                        ),
                    ],
                ),
                codepipeline.StageProps(
                    stage_name="Invalidate",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="InvalidateCloudFront",
                            project=invalidation_project,
                            input=build_output,
                        ),
                    ],
                ),
            ],
        )

        # Grant the pipeline role permission to start the CodeBuild projects
        pipeline.role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=[
                    "codebuild:StartBuild",
                    "codebuild:StopBuild",
                    "codebuild:BatchGetBuilds",
                ],
                resources=[build_project.project_arn, invalidation_project.project_arn],
            )
        )

        # -- SSM exports -----------------------------------------------------
        ssm.StringParameter(
            self,
            "DistributionDomainParam",
            parameter_name=get_ssm_parameter_path(
                p, e, "frontend", "distribution-domain"
            ),
            string_value=distribution.distribution_domain_name,
            description="CloudFront distribution domain name",
        )

        # -- Outputs ---------------------------------------------------------
        CfnOutput(
            self,
            "DistributionDomainName",
            value=distribution.distribution_domain_name,
            description="CloudFront distribution URL — point your CNAME here",
        )

        if domain_name:
            CfnOutput(
                self,
                "CustomDomain",
                value=f"https://{domain_name}",
                description="Custom domain URL",
            )
