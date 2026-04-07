import aws_cdk as cdk
from aws_cdk import Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as sns_subs
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from helpers.naming import get_resource_name, get_ssm_parameter_path


class ApiStack(Stack):
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
        api_name = get_resource_name(project_name, env_name, "api-gateway")

        # ── SSM Lookups ────────────────────────────────────────────
        user_pool_id = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(project_name, env_name, "auth", "user-pool-id"),
        )

        user_pool = cognito.UserPool.from_user_pool_id(
            self, "ImportedUserPool", user_pool_id
        )

        # Lambda function ARNs from SSM
        function_purposes = [
            "generate-upload-presigned-urls",
            "scan-worker",
            "get-scan-result",
            "create-asset",
            "approve-asset",
            "create-user",
            "deactivate-user",
            "reactivate-user",
            "list-users",
            # Phase 2 — Handover
            "assign-asset",
            "get-handover-form",
            "get-signed-handover-form",
            "generate-signature-upload-url",
            "accept-handover",
            "list-assets",
            "cancel-assignment",
            "list-employee-signatures",
            "list-pending-signatures",
            # Phase 3 — Software Installation Governance
            "submit-software-request",
            "list-software-requests",
            "get-software-request",
            "review-software-request",
            "management-review-software-request",
            "list-all-software-requests",
            # Phase 4 — Issue Management
            "submit-issue",
            "resolve-repair",
            "send-warranty",
            "complete-repair",
            "request-replacement",
            "management-review-issue",
            "list-issues",
            "get-issue",
            "list-pending-replacements",
            "list-all-issues",
            # Phase 4 — Issue Upload URLs
            "generate-issue-upload-urls",
            # Phase 5 — Asset Return
            "initiate-return",
            "generate-return-upload-urls",
            "submit-admin-return-evidence",
            "generate-return-signature-upload-url",
            "complete-return",
            "list-returns",
            "get-return",
            "list-all-returns",
            # Phase 6 — Asset Disposal
            "initiate-disposal",
            "management-review-disposal",
            "complete-disposal",
            "list-disposals",
            "list-pending-disposals",
            "get-disposal-details",
            "list-asset-disposals",
            # Scan — SNS-triggered (no API route, but needs SSM ARN for lookup)
            "scan-result-processor",
            # Asset details
            "get-asset",
            "get-asset-logs",
            # Notifications
            "list-my-notifications",
            "mark-notification-read",
            # Asset Categories
            "create-asset-category",
            "delete-asset-category",
            "list-asset-categories",
            # Dashboard Counters
            "get-dashboard-counters",
            # Dashboard Stats
            "get-it-admin-stats",
            "get-management-stats",
            "get-employee-stats",
            "get-finance-stats",
            "get-asset-distribution",
            "get-recent-activity",
            "get-approval-hub",
            # Page Stats
            "get-assets-page-stats",
            "get-requests-it-admin-stats",
            "get-requests-employee-stats",
        ]

        lambda_functions = {}
        for purpose in function_purposes:
            fn_arn = ssm.StringParameter.value_for_string_parameter(
                self,
                get_ssm_parameter_path(
                    project_name, env_name, "functions", f"{purpose}-arn"
                ),
            )
            construct_id_name = purpose.replace("-", " ").title().replace(" ", "")
            lambda_functions[purpose] = lambda_.Function.from_function_attributes(
                self,
                f"Imported{construct_id_name}Fn",
                function_arn=fn_arn,
                same_environment=True,
            )

        # ── API Gateway ───────────────────────────────────────────
        api = apigw.RestApi(
            self,
            "APIGateway",
            rest_api_name=api_name,
            deploy_options=apigw.StageOptions(stage_name=env_name),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Api-Key",
                ],
            ),
        )

        # Export REST API ID to SSM for cross-stack consumers
        ssm.StringParameter(
            self,
            "RestApiIdParam",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "api", "rest-api-id"
            ),
            string_value=api.rest_api_id,
            description="API Gateway REST API ID",
        )

        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
        )

        auth_kwargs = dict(
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        def lambda_integration(fn):
            return apigw.LambdaIntegration(fn)

        # ── Phase 1 Routes ────────────────────────────────────────
        # /assets
        assets_resource = api.root.add_resource("assets")

        # POST /assets → CreateAsset
        assets_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["create-asset"]),
            **auth_kwargs,
        )

        # /assets/uploads
        uploads_resource = assets_resource.add_resource("uploads")

        # POST /assets/uploads → GenerateUploadUrls
        uploads_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["generate-upload-presigned-urls"]),
            **auth_kwargs,
        )

        # /assets/scan
        scan_resource = assets_resource.add_resource("scan")

        # /assets/scan/{scan_job_id}
        scan_job_resource = scan_resource.add_resource("{scan_job_id}")

        # GET /assets/scan/{scan_job_id} → GetScanResults
        scan_job_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-scan-result"]),
            **auth_kwargs,
        )

        # GET /assets → ListAssets
        assets_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-assets"]),
            **auth_kwargs,
        )

        # ── Phase 2 Routes — Handover ────────────────────────────

        # /assets/{asset_id}
        asset_id_resource = assets_resource.add_resource("{asset_id}")

        # GET /assets/{asset_id} → GetAsset
        asset_id_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-asset"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/logs
        asset_logs_resource = asset_id_resource.add_resource("logs")

        # GET /assets/{asset_id}/logs → GetAssetLogs
        asset_logs_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-asset-logs"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/approve
        approve_resource = asset_id_resource.add_resource("approve")

        # PUT /assets/{asset_id}/approve → ApproveAsset
        approve_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["approve-asset"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/assign
        assign_resource = asset_id_resource.add_resource("assign")

        # POST /assets/{asset_id}/assign → AssignAsset
        assign_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["assign-asset"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/assign-pdf-form
        assign_pdf_form_resource = asset_id_resource.add_resource("assign-pdf-form")

        # GET /assets/{asset_id}/assign-pdf-form → GetHandoverForm
        assign_pdf_form_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-handover-form"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/signed-pdf-form
        signed_pdf_form_resource = asset_id_resource.add_resource("signed-pdf-form")

        # GET /assets/{asset_id}/signed-pdf-form → GetSignedHandoverForm
        signed_pdf_form_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-signed-handover-form"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/signature-upload-url
        signature_upload_resource = asset_id_resource.add_resource(
            "signature-upload-url"
        )

        # POST /assets/{asset_id}/signature-upload-url → GenerateSignatureUploadUrl
        signature_upload_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["generate-signature-upload-url"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/accept
        accept_resource = asset_id_resource.add_resource("accept")

        # PUT /assets/{asset_id}/accept → AcceptHandover
        accept_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["accept-handover"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/cancel-assignment
        cancel_assignment_resource = asset_id_resource.add_resource("cancel-assignment")

        # DELETE /assets/{asset_id}/cancel-assignment → CancelAssignment
        cancel_assignment_resource.add_method(
            "DELETE",
            lambda_integration(lambda_functions["cancel-assignment"]),
            **auth_kwargs,
        )

        # ── User Management Routes ───────────────────────────────
        # /users
        users_resource = api.root.add_resource("users")

        # GET /users → ListUsers
        users_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-users"]),
            **auth_kwargs,
        )

        # /users/create
        users_create_resource = users_resource.add_resource("create")

        # POST /users/create → CreateUser
        users_create_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["create-user"]),
            **auth_kwargs,
        )

        # /users/{id}
        user_id_resource = users_resource.add_resource("{id}")

        # /users/{id}/deactivate
        deactivate_resource = user_id_resource.add_resource("deactivate")

        # DELETE /users/{id}/deactivate → DeactivateUser
        deactivate_resource.add_method(
            "DELETE",
            lambda_integration(lambda_functions["deactivate-user"]),
            **auth_kwargs,
        )

        # /users/{id}/reactivate
        reactivate_resource = user_id_resource.add_resource("reactivate")

        # PUT /users/{id}/reactivate → ReactivateUser
        reactivate_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["reactivate-user"]),
            **auth_kwargs,
        )

        # /users/{id}/signatures
        signatures_resource = user_id_resource.add_resource("signatures")

        # GET /users/{id}/signatures → ListEmployeeSignatures
        signatures_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-employee-signatures"]),
            **auth_kwargs,
        )

        # /users/me/pending-signatures
        me_resource = users_resource.add_resource("me")
        pending_signatures_resource = me_resource.add_resource("pending-signatures")

        # GET /users/me/pending-signatures → ListPendingSignatures
        pending_signatures_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-pending-signatures"]),
            **auth_kwargs,
        )

        # ── Phase 3 Routes — Software Installation Governance ──

        # /assets/{asset_id}/software-requests
        software_requests_resource = asset_id_resource.add_resource("software-requests")

        # POST /assets/{asset_id}/software-requests → SubmitSoftwareRequest
        software_requests_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["submit-software-request"]),
            **auth_kwargs,
        )

        # GET /assets/{asset_id}/software-requests → ListSoftwareRequests
        software_requests_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-software-requests"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/software-requests/{software_request_id}
        software_request_timestamp_resource = software_requests_resource.add_resource(
            "{software_request_id}"
        )

        # GET /assets/{asset_id}/software-requests/{software_request_id} → GetSoftwareRequest
        software_request_timestamp_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-software-request"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/software-requests/{software_request_id}/review
        review_sw_resource = software_request_timestamp_resource.add_resource("review")

        # PUT /assets/{asset_id}/software-requests/{software_request_id}/review → ReviewSoftwareRequest
        review_sw_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["review-software-request"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/software-requests/{software_request_id}/management-review
        management_review_resource = software_request_timestamp_resource.add_resource(
            "management-review"
        )

        # PUT /assets/{asset_id}/software-requests/{software_request_id}/management-review → ManagementReviewSoftwareRequest
        management_review_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["management-review-software-request"]),
            **auth_kwargs,
        )

        # /assets/software-requests (all software requests — before {asset_id} resource)
        all_software_requests_resource = assets_resource.add_resource(
            "software-requests"
        )

        # GET /assets/software-requests → ListAllSoftwareRequests
        all_software_requests_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-all-software-requests"]),
            **auth_kwargs,
        )

        # ── Phase 4 Routes — Issue Management ──────────────────

        # /assets/{asset_id}/issues
        issues_resource = asset_id_resource.add_resource("issues")

        # POST /assets/{asset_id}/issues → SubmitIssue
        issues_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["submit-issue"]),
            **auth_kwargs,
        )

        # GET /assets/{asset_id}/issues → ListIssues
        issues_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-issues"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/issues/{issue_id}
        issue_timestamp_resource = issues_resource.add_resource("{issue_id}")

        # GET /assets/{asset_id}/issues/{issue_id} → GetIssue
        issue_timestamp_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-issue"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/issues/{issue_id}/upload-urls
        issue_upload_urls_resource = issue_timestamp_resource.add_resource(
            "upload-urls"
        )

        # POST /assets/{asset_id}/issues/{issue_id}/upload-urls → GenerateIssueUploadUrls
        issue_upload_urls_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["generate-issue-upload-urls"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/issues/{issue_id}/resolve-repair
        resolve_repair_resource = issue_timestamp_resource.add_resource(
            "resolve-repair"
        )

        # PUT /assets/{asset_id}/issues/{issue_id}/resolve-repair → ResolveRepair
        resolve_repair_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["resolve-repair"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/issues/{issue_id}/send-warranty
        send_warranty_resource = issue_timestamp_resource.add_resource("send-warranty")

        # PUT /assets/{asset_id}/issues/{issue_id}/send-warranty → SendWarranty
        send_warranty_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["send-warranty"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/issues/{issue_id}/complete-repair
        complete_repair_resource = issue_timestamp_resource.add_resource(
            "complete-repair"
        )

        # PUT /assets/{asset_id}/issues/{issue_id}/complete-repair → CompleteRepair
        complete_repair_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["complete-repair"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/issues/{issue_id}/request-replacement
        request_replacement_resource = issue_timestamp_resource.add_resource(
            "request-replacement"
        )

        # PUT /assets/{asset_id}/issues/{issue_id}/request-replacement → RequestReplacement
        request_replacement_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["request-replacement"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/issues/{issue_id}/management-review
        mgmt_review_issue_resource = issue_timestamp_resource.add_resource(
            "management-review"
        )

        # PUT /assets/{asset_id}/issues/{issue_id}/management-review → ManagementReviewIssue
        mgmt_review_issue_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["management-review-issue"]),
            **auth_kwargs,
        )

        # /issues (top-level, under api.root)
        issues_root_resource = api.root.add_resource("issues")

        # /issues/pending-replacements
        pending_replacements_resource = issues_root_resource.add_resource(
            "pending-replacements"
        )

        # GET /issues/pending-replacements → ListPendingReplacements
        pending_replacements_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-pending-replacements"]),
            **auth_kwargs,
        )

        # GET /issues → ListAllIssues
        issues_root_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-all-issues"]),
            **auth_kwargs,
        )

        # ── Phase 5 Routes — Asset Return ──────────────────────

        # /returns (top-level, under api.root)
        returns_root_resource = api.root.add_resource("returns")

        # GET /returns → ListAllReturns
        returns_root_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-all-returns"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/returns
        returns_resource = asset_id_resource.add_resource("returns")

        # POST /assets/{asset_id}/returns → InitiateReturn
        returns_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["initiate-return"]),
            **auth_kwargs,
        )

        # GET /assets/{asset_id}/returns → ListReturns
        returns_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-returns"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/returns/{return_id}
        return_timestamp_resource = returns_resource.add_resource("{return_id}")

        # GET /assets/{asset_id}/returns/{return_id} → GetReturn
        return_timestamp_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-return"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/returns/{return_id}/upload-urls
        return_upload_urls_resource = return_timestamp_resource.add_resource(
            "upload-urls"
        )

        # POST /assets/{asset_id}/returns/{return_id}/upload-urls → GenerateReturnUploadUrls
        return_upload_urls_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["generate-return-upload-urls"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/returns/{return_id}/submit-evidence
        return_submit_evidence_resource = return_timestamp_resource.add_resource(
            "submit-evidence"
        )

        # POST /assets/{asset_id}/returns/{return_id}/submit-evidence → SubmitAdminReturnEvidence
        return_submit_evidence_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["submit-admin-return-evidence"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/returns/{return_id}/signature-upload-url
        return_sig_upload_resource = return_timestamp_resource.add_resource(
            "signature-upload-url"
        )

        # POST /assets/{asset_id}/returns/{return_id}/signature-upload-url → GenerateReturnSignatureUploadUrl
        return_sig_upload_resource.add_method(
            "POST",
            lambda_integration(
                lambda_functions["generate-return-signature-upload-url"]
            ),
            **auth_kwargs,
        )

        # /assets/{asset_id}/returns/{return_id}/complete
        return_complete_resource = return_timestamp_resource.add_resource("complete")

        # PUT /assets/{asset_id}/returns/{return_id}/complete → CompleteReturn
        return_complete_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["complete-return"]),
            **auth_kwargs,
        )

        # ── Top-Level Software Requests Route ─────────────────

        # /software-requests (top-level, under api.root)
        software_requests_root_resource = api.root.add_resource("software-requests")

        # GET /software-requests → ListAllSoftwareRequests
        software_requests_root_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-all-software-requests"]),
            **auth_kwargs,
        )

        # ── Phase 6 Routes — Asset Disposal ───────────────────

        # /assets/{asset_id}/disposals
        disposals_resource = asset_id_resource.add_resource("disposals")

        # POST /assets/{asset_id}/disposals → InitiateDisposal
        disposals_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["initiate-disposal"]),
            **auth_kwargs,
        )

        # GET /assets/{asset_id}/disposals → ListAssetDisposals
        disposals_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-asset-disposals"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/disposals/{disposal_id}
        disposal_id_resource = disposals_resource.add_resource("{disposal_id}")

        # GET /assets/{asset_id}/disposals/{disposal_id} → GetDisposalDetails
        disposal_id_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-disposal-details"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/disposals/{disposal_id}/management-review
        disposal_mgmt_review_resource = disposal_id_resource.add_resource(
            "management-review"
        )

        # PUT /assets/{asset_id}/disposals/{disposal_id}/management-review → ManagementReviewDisposal
        disposal_mgmt_review_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["management-review-disposal"]),
            **auth_kwargs,
        )

        # /assets/{asset_id}/disposals/{disposal_id}/complete
        disposal_complete_resource = disposal_id_resource.add_resource("complete")

        # PUT /assets/{asset_id}/disposals/{disposal_id}/complete → CompleteDisposal
        disposal_complete_resource.add_method(
            "PUT",
            lambda_integration(lambda_functions["complete-disposal"]),
            **auth_kwargs,
        )

        # /disposals (top-level, under api.root)
        disposals_root_resource = api.root.add_resource("disposals")

        # GET /disposals → ListDisposals
        disposals_root_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-disposals"]),
            **auth_kwargs,
        )

        # /disposals/pending
        disposals_pending_resource = disposals_root_resource.add_resource("pending")

        # GET /disposals/pending → ListPendingDisposals
        disposals_pending_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-pending-disposals"]),
            **auth_kwargs,
        )

        # ── Notification Routes ──────────────────────────────────

        # /notifications
        notifications_resource = api.root.add_resource("notifications")

        # GET /notifications → ListMyNotifications
        notifications_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-my-notifications"]),
            **auth_kwargs,
        )

        # /notifications/{notification_id}
        notification_id_resource = notifications_resource.add_resource(
            "{notification_id}"
        )

        # PATCH /notifications/{notification_id} → MarkNotificationRead
        notification_id_resource.add_method(
            "PATCH",
            lambda_integration(lambda_functions["mark-notification-read"]),
            **auth_kwargs,
        )

        # ── Asset Category Routes ─────────────────────────────

        # /categories
        categories_resource = api.root.add_resource("categories")

        # POST /categories → CreateAssetCategory
        categories_resource.add_method(
            "POST",
            lambda_integration(lambda_functions["create-asset-category"]),
            **auth_kwargs,
        )

        # GET /categories → ListAssetCategories
        categories_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["list-asset-categories"]),
            **auth_kwargs,
        )

        # /categories/{category_id}
        category_id_resource = categories_resource.add_resource("{category_id}")

        # DELETE /categories/{category_id} → DeleteAssetCategory
        category_id_resource.add_method(
            "DELETE",
            lambda_integration(lambda_functions["delete-asset-category"]),
            **auth_kwargs,
        )

        # ── Dashboard Routes ──────────────────────────────────

        # /dashboard
        dashboard_resource = api.root.add_resource("dashboard")

        # /dashboard/counters
        counters_resource = dashboard_resource.add_resource("counters")

        # GET /dashboard/counters → GetDashboardCounters
        counters_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-dashboard-counters"]),
            **auth_kwargs,
        )

        # /dashboard/it-admin
        it_admin_resource = dashboard_resource.add_resource("it-admin")

        # /dashboard/it-admin/stats
        it_admin_stats_resource = it_admin_resource.add_resource("stats")

        # GET /dashboard/it-admin/stats → GetITAdminStats
        it_admin_stats_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-it-admin-stats"]),
            **auth_kwargs,
        )

        # /dashboard/management
        management_resource = dashboard_resource.add_resource("management")

        # /dashboard/management/stats
        management_stats_resource = management_resource.add_resource("stats")

        # GET /dashboard/management/stats → GetManagementStats
        management_stats_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-management-stats"]),
            **auth_kwargs,
        )

        # /dashboard/management/approval-hub
        approval_hub_resource = management_resource.add_resource("approval-hub")

        # GET /dashboard/management/approval-hub → GetApprovalHub
        approval_hub_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-approval-hub"]),
            **auth_kwargs,
        )

        # /dashboard/employee
        employee_resource = dashboard_resource.add_resource("employee")

        # /dashboard/employee/stats
        employee_stats_resource = employee_resource.add_resource("stats")

        # GET /dashboard/employee/stats → GetEmployeeStats
        employee_stats_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-employee-stats"]),
            **auth_kwargs,
        )

        # /dashboard/finance
        finance_resource = dashboard_resource.add_resource("finance")

        # /dashboard/finance/stats
        finance_stats_resource = finance_resource.add_resource("stats")

        # GET /dashboard/finance/stats → GetFinanceStats
        finance_stats_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-finance-stats"]),
            **auth_kwargs,
        )

        # /dashboard/asset-distribution
        asset_distribution_resource = dashboard_resource.add_resource(
            "asset-distribution"
        )

        # GET /dashboard/asset-distribution → GetAssetDistribution
        asset_distribution_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-asset-distribution"]),
            **auth_kwargs,
        )

        # /dashboard/recent-activity
        recent_activity_resource = dashboard_resource.add_resource("recent-activity")

        # GET /dashboard/recent-activity → GetRecentActivity
        recent_activity_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-recent-activity"]),
            **auth_kwargs,
        )

        # ── Page Stats Routes ─────────────────────────────────

        # /pages
        pages_resource = api.root.add_resource("pages")

        # /pages/assets
        pages_assets_resource = pages_resource.add_resource("assets")

        # /pages/assets/stats
        pages_assets_stats_resource = pages_assets_resource.add_resource("stats")

        # GET /pages/assets/stats → GetAssetsPageStats
        pages_assets_stats_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-assets-page-stats"]),
            **auth_kwargs,
        )

        # /pages/requests
        pages_requests_resource = pages_resource.add_resource("requests")

        # /pages/requests/it-admin
        pages_requests_it_admin_resource = pages_requests_resource.add_resource(
            "it-admin"
        )

        # /pages/requests/it-admin/stats
        pages_requests_it_admin_stats_resource = (
            pages_requests_it_admin_resource.add_resource("stats")
        )

        # GET /pages/requests/it-admin/stats → GetRequestsITAdminStats
        pages_requests_it_admin_stats_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-requests-it-admin-stats"]),
            **auth_kwargs,
        )

        # /pages/requests/employee
        pages_requests_employee_resource = pages_requests_resource.add_resource(
            "employee"
        )

        # /pages/requests/employee/stats
        pages_requests_employee_stats_resource = (
            pages_requests_employee_resource.add_resource("stats")
        )

        # GET /pages/requests/employee/stats → GetRequestsEmployeeStats
        pages_requests_employee_stats_resource.add_method(
            "GET",
            lambda_integration(lambda_functions["get-requests-employee-stats"]),
            **auth_kwargs,
        )

        # ── CloudWatch Alarms ─────────────────────────────────

        # SNS topic for alarm notifications
        alarm_topic = sns.Topic(
            self,
            "ApiAlarmTopic",
            topic_name=get_resource_name(project_name, env_name, "api-alarms"),
            display_name=f"{project_name}-{env_name} API Gateway Alarms",
        )

        # Email subscription from SSM
        alarm_email = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "notifications", "alarm-email"
            ),
        )
        alarm_topic.add_subscription(sns_subs.EmailSubscription(alarm_email))

        alarm_action = cw_actions.SnsAction(alarm_topic)

        # 5XX errors — server-side / Lambda failures
        # Triggers if any 5XX errors occur in a 1-minute window
        api.metric_server_error(
            period=cdk.Duration.minutes(1),
            statistic="Sum",
        ).create_alarm(
            self,
            "Api5xxAlarm",
            alarm_name=get_resource_name(project_name, env_name, "api-5xx-errors"),
            alarm_description="API Gateway 5XX error rate is elevated",
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(
            alarm_action
        )

        # 4XX errors — client-side errors (auth failures, bad requests)
        # Triggers if 4XX errors exceed 10 in a 5-minute window
        api.metric_client_error(
            period=cdk.Duration.minutes(5),
            statistic="Sum",
        ).create_alarm(
            self,
            "Api4xxAlarm",
            alarm_name=get_resource_name(project_name, env_name, "api-4xx-errors"),
            alarm_description="API Gateway 4XX error rate is elevated",
            threshold=50,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(
            alarm_action
        )

        # p99 latency — triggers if 99th percentile latency exceeds 5 seconds
        api.metric_latency(
            period=cdk.Duration.minutes(5),
            statistic="p99",
        ).create_alarm(
            self,
            "ApiLatencyP99Alarm",
            alarm_name=get_resource_name(project_name, env_name, "api-latency-p99"),
            alarm_description="API Gateway p99 latency exceeded 5 seconds",
            threshold=5000,  # milliseconds
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(
            alarm_action
        )

        # Integration latency — time spent in Lambda (excludes API GW overhead)
        # Triggers if p99 integration latency exceeds 10 seconds (Lambda timeout signal)
        api.metric_integration_latency(
            period=cdk.Duration.minutes(5),
            statistic="p99",
        ).create_alarm(
            self,
            "ApiIntegrationLatencyAlarm",
            alarm_name=get_resource_name(
                project_name, env_name, "api-integration-latency"
            ),
            alarm_description="API Gateway integration (Lambda) p99 latency exceeded 10 seconds",
            threshold=10000,  # milliseconds
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(
            alarm_action
        )
