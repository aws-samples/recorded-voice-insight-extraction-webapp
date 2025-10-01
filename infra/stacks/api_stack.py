# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import boto3
import os
from aws_cdk import Aws
from aws_cdk import CfnOutput, Duration, NestedStack, RemovalPolicy, aws_logs
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk.aws_bedrock import CfnKnowledgeBase
import aws_cdk.aws_s3 as s3
from aws_cdk import aws_ssm as ssm


class ReVIEWAPIStack(NestedStack):
    """Construct for API Gateway separating frontend and backend.
    REST endpoints associated with backend lambdas are provided for the frontend.
    Cognito is used for API auth."""

    def __init__(
        self,
        scope,
        props: dict,
        llm_lambda: _lambda.Function,
        ddb_lambda: _lambda.Function,
        knowledge_base: CfnKnowledgeBase,
        presigned_url_lambda: _lambda.Function,
        kb_job_deletion_lambda: _lambda.Function,
        subtitle_lambda: _lambda.Function,
        analysis_templates_lambda: _lambda.Function,
        source_bucket: s3.Bucket,
        **kwargs,
    ):
        self.props = props
        construct_id = props["stack_name_base"] + "-api"
        description = "ReVIEW Application - API stack"
        super().__init__(scope, construct_id, description=description, **kwargs)

        self.bucket = source_bucket
        self.setup_cognito_pool()
        self.enable_API_GW_logging()
        self.create_REST_gateway()
        self.associate_lambda_with_gateway(llm_lambda, "llm")
        self.associate_lambda_with_gateway(ddb_lambda, "ddb")
        # self.associate_lambda_with_gateway(kb_query_lambda, "kb")
        self.associate_lambda_with_gateway(presigned_url_lambda, "s3-presigned")
        self.associate_lambda_with_gateway(kb_job_deletion_lambda, "kb-job-deletion")
        self.associate_lambda_with_gateway(subtitle_lambda, "subtitles")
        self.associate_lambda_with_gateway_crud(
            analysis_templates_lambda, "analysis-templates"
        )

        # Create DynamoDB table for WebSocket session management
        self.websocket_session_table = self.create_websocket_session_table()

        # Create async streaming processor Lambda
        self.async_streaming_lambda = self.create_async_streaming_lambda(knowledge_base)

        # Create lambda to query knowledge base (and stream responses to websocket)
        self.kb_query_lambda = self.create_query_lambda(knowledge_base)

        # Create the websocket API (without authorizer - auth moved to message body)
        self.create_WS_gateway(self.kb_query_lambda)

        # Add WS GW URL to KB lambda as env variable
        # Lambda needs https://* url
        # self.web_socket_api_stage.url is wss://*
        # self.web_socket_api_stage.callback_url is https://
        self.kb_query_lambda.add_environment(
            "WS_API_URL", self.web_socket_api_stage.callback_url
        )

        # Output the API URLs
        CfnOutput(self, "RESTApiUrl", value=self.api.url)
        CfnOutput(self, "WSApiUrl", value=self.web_socket_api_stage.url)

        # Store configuration in SSM Parameter Store for frontend to access
        self.store_config_in_ssm()

    def setup_cognito_pool(self):
        # Cognito User Pool (stored as self.cognito_user_pool)
        user_pool_common_config = {
            "id": "review-app-cognito-user-pool-id",
            "user_pool_name": self.props["cognito_pool_name"],
            "auto_verify": cognito.AutoVerifiedAttrs(email=True),
            "removal_policy": RemovalPolicy.RETAIN,
            "password_policy": cognito.PasswordPolicy(
                min_length=8,
                require_digits=False,
                require_lowercase=False,
                require_uppercase=False,
                require_symbols=False,
            ),
            "account_recovery": cognito.AccountRecovery.EMAIL_ONLY,
            "advanced_security_mode": cognito.AdvancedSecurityMode.ENFORCED,
            "deletion_protection": True,
        }

        # Check if a user pool with this name already exists, else create one
        # Unfortunately currently there is no way to do this w/ constructs
        # (only search by ID, which I don't have a priori)
        cognito_region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
        cognito_client = boto3.client("cognito-idp", cognito_region)
        existing_pools = cognito_client.list_user_pools(MaxResults=10)["UserPools"]
        found_existing_pool = False
        for pool in existing_pools:
            if pool["Name"] == self.props["cognito_pool_name"]:
                self.cognito_user_pool = cognito.UserPool.from_user_pool_id(
                    self, "review-app-cognito-user-pool", user_pool_id=pool["Id"]
                )
                found_existing_pool = True
                break

        if not found_existing_pool:
            # Create a new user pool
            self.cognito_user_pool = cognito.UserPool(self, **user_pool_common_config)

        # Create Cognito user pool client for frontend authentication
        self.cognito_user_pool_client = self.cognito_user_pool.add_client(
            "review-app-cognito-client",
            user_pool_client_name="review-app-cognito-client",
            generate_secret=False,
            access_token_validity=Duration.hours(8),
            id_token_validity=Duration.hours(8),
            auth_flows=cognito.AuthFlow(user_srp=True),
        )

    def enable_API_GW_logging(self):
        cloud_watch_role = iam.Role(
            self,
            "ApiGatewayCloudWatchLoggingRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            inline_policies={
                f"{self.props['stack_name_base']}-CloudWatchLogsPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:DescribeLogGroups",
                                "logs:DescribeLogStreams",
                                "logs:PutLogEvents",
                                "logs:GetLogEvents",
                                "logs:FilterLogEvents",
                            ],
                            resources=[f"arn:aws:logs:{Aws.REGION}:{Aws.ACCOUNT_ID}:*"],
                        )
                    ]
                )
            },
        )

        apigw_account = apigw.CfnAccount(  # noqa
            self, "ApiGatewayAccount", cloud_watch_role_arn=cloud_watch_role.role_arn
        )

    def create_REST_gateway(self):
        # Create API Gateway and Cognito authorizer

        self.api = apigw.RestApi(
            self,
            f"{self.props['stack_name_base']}-api",
            rest_api_name=f"{self.props['stack_name_base']}-api",
            description="API for ReVIEW application",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,  # All origins allowed
                allow_methods=apigw.Cors.ALL_METHODS,  # All methods have an authorizer
            ),
            deploy=True,
        )

        self.api.apply_removal_policy(RemovalPolicy.DESTROY)

        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "ReVIEWAPIAuthorizer",
            cognito_user_pools=[self.cognito_user_pool],
            identity_source=apigw.IdentitySource.header(
                "Authorization"
            ),  # This is the header expression which includes the bearer token
            results_cache_ttl=Duration.seconds(0),  # Disable caching
        )

    def create_websocket_session_table(self) -> dynamodb.Table:
        """Create DynamoDB table for WebSocket session management and message chunking"""
        table = dynamodb.Table(
            self,
            f"{self.props['stack_name_base']}-WebSocketSessionTable",
            table_name=f"{self.props['stack_name_base']}-websocket-sessions",
            partition_key=dynamodb.Attribute(
                name="ConnectionId", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="MessagePartId", type=dynamodb.AttributeType.NUMBER
            ),
            # TTL for automatic cleanup of expired sessions
            time_to_live_attribute="expire",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        return table

    def associate_lambda_with_gateway(
        self, my_lambda: _lambda.Function, resource_name: str
    ):
        # Create a resource for the Lambda function
        resource = self.api.root.add_resource(resource_name)

        # Integrate Lambda function with API Gateway
        # Lambda functions now handle CORS headers themselves
        integration = apigw.LambdaIntegration(my_lambda)

        # Add POST method to resource, with Cognito authorizer
        resource.add_method(
            "POST",
            integration,
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

    def associate_lambda_with_gateway_get(
        self, my_lambda: _lambda.Function, resource_name: str
    ):
        # Create a resource for the Lambda function
        resource = self.api.root.add_resource(resource_name)

        # Integrate Lambda function with API Gateway
        # Lambda functions now handle CORS headers themselves
        integration = apigw.LambdaIntegration(my_lambda)

        # Add GET method to resource, with Cognito authorizer
        resource.add_method(
            "GET",
            integration,
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

    def associate_lambda_with_gateway_crud(
        self, my_lambda: _lambda.Function, resource_name: str
    ):
        # Create a resource for the Lambda function
        resource = self.api.root.add_resource(resource_name)

        # Integrate Lambda function with API Gateway
        # Lambda functions now handle CORS headers themselves
        integration = apigw.LambdaIntegration(my_lambda)

        # Add CRUD methods to resource, with Cognito authorizer
        for method in ["GET", "POST", "PUT", "DELETE"]:
            resource.add_method(
                method,
                integration,
                authorizer=self.authorizer,
                authorization_type=apigw.AuthorizationType.COGNITO,
            )

        # Add a sub-resource for operations on specific template IDs
        template_resource = resource.add_resource("{template_id}")
        for method in ["GET", "PUT", "DELETE"]:
            template_resource.add_method(
                method,
                integration,
                authorizer=self.authorizer,
                authorization_type=apigw.AuthorizationType.COGNITO,
            )

    def create_WS_gateway(self, kb_query_lambda):
        self.web_socket_api = apigwv2.WebSocketApi(
            self, "web_socket_api", route_selection_expression="$request.body.step"
        )
        # Create a log group for WebSocket API access logs
        log_group = aws_logs.LogGroup(
            self,
            "ReVIEWWebSocketApiLogs",
            retention=aws_logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.web_socket_api_stage = apigwv2.WebSocketStage(
            self,
            "web_socket_api_stage",
            web_socket_api=self.web_socket_api,
            stage_name="prod",  # Changed from "dev" to "prod" to match React frontend URL
            auto_deploy=True,
        )

        # Cast to CfnStage to configure logging
        cfn_stage = self.web_socket_api_stage.node.default_child
        cfn_stage.access_log_settings = {
            "destinationArn": log_group.log_group_arn,
            "format": '$context.identity.sourceIp - - [$context.requestTime] "$context.routeKey $context.connectionId" $context.status $context.responseLength $context.requestId $context.error.message $context.error.messageString $context.integrationErrorMessage',
        }

        # Add default route settings including throttling and logging
        cfn_stage.default_route_settings = {
            "throttling_burst_limit": 500,
            "throttling_rate_limit": 1000,
            "data_trace_enabled": True,
            "logging_level": "INFO",
            "detailed_metrics_enabled": True,
        }

        connect_disconnect_lambda_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-WSConnectDisconnectLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                ),
            ],
        )

        disconnect_lambda = _lambda.Function(
            self,
            "disconnect_lambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("lambdas"),
            handler="websockets.disconnect-lambda.lambda_handler",
            role=connect_disconnect_lambda_role,
            timeout=Duration.seconds(600),
        )
        connect_lambda = _lambda.Function(
            self,
            "connect_lambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("lambdas"),
            handler="websockets.connect-lambda.lambda_handler",
            role=connect_disconnect_lambda_role,
            timeout=Duration.seconds(600),
        )

        # Default route handles all WebSocket messages (START, BODY, END steps)
        self.web_socket_api.add_route(
            "$default",
            integration=integrations.WebSocketLambdaIntegration(
                "default", handler=kb_query_lambda
            ),
            return_response=True,
        )
        self.web_socket_api.add_route(
            "$connect",
            integration=integrations.WebSocketLambdaIntegration(
                "connect", handler=connect_lambda
            ),
            # No authorizer - auth moved to message body
            return_response=True,
        )
        self.web_socket_api.add_route(
            "$disconnect",
            integration=integrations.WebSocketLambdaIntegration(
                "disconnect", handler=disconnect_lambda
            ),
            return_response=True,
        )

    def create_async_streaming_lambda(self, knowledge_base: CfnKnowledgeBase) -> _lambda.Function:
        """Create async Lambda for streaming LLM responses"""
        
        async_streaming_lambda = _lambda.Function(
            self,
            f"{self.props['stack_name_base']}-AsyncStreamingLambda",
            function_name=f"{self.props['stack_name_base']}-AsyncStreamingLambda",
            description="Async Lambda for streaming LLM responses to WebSocket",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="websockets.async_streaming_processor.handler",
            code=_lambda.Code.from_asset("lambdas"),
            timeout=Duration.minutes(15),  # Max Lambda timeout for long streaming
            environment={
                "KNOWLEDGE_BASE_ID": knowledge_base.attr_knowledge_base_id,
                "FOUNDATION_MODEL_ID": self.props["llm_model_id"],
                "NUM_CHUNKS": self.props["kb_num_chunks"],
                "S3_BUCKET": self.bucket.bucket_name,
                "TEXT_TRANSCRIPTS_PREFIX": self.props["s3_text_transcripts_prefix"],
                "BDA_OUTPUT_PREFIX": self.props["s3_bda_processed_output_prefix"],
            },
            role=self.create_async_streaming_lambda_role(knowledge_base=knowledge_base),
        )

        return async_streaming_lambda

    def create_async_streaming_lambda_role(self, knowledge_base: CfnKnowledgeBase) -> iam.Role:
        """Create role for async streaming Lambda"""
        async_streaming_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-AsyncStreamingLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                )
            ],
            inline_policies={
                "s3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:GetObject", "s3:ListBucket"],
                            resources=[f"{self.bucket.bucket_arn}*"],
                        )
                    ]
                ),
            },
        )
        
        # Add API Gateway WebSocket permissions
        async_streaming_role.add_to_policy(
            iam.PolicyStatement(
                actions=["execute-api:ManageConnections"],
                resources=[
                    "arn:aws:execute-api:*:*:*/*/DELETE/@connections/*",
                    "arn:aws:execute-api:*:*:*/*/POST/@connections/*",
                ],
            )
        )
        
        # Add Bedrock permissions
        async_streaming_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:Retrieve",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        async_streaming_role.apply_removal_policy(RemovalPolicy.DESTROY)
        return async_streaming_role
        """Create a role that allows lambda query Bedrock KB"""
        query_lambda_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-KBQueryLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                )
            ],
            # Lambda sometimes reads transcripts from s3
            inline_policies={
                "s3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:GetObject", "s3:ListBucket"],
                            resources=[f"{self.bucket.bucket_arn}*"],
                        )
                    ]
                ),
            },
            #     # KB lambda needs to post to websocket API gateway
            #     iam.ManagedPolicy.from_aws_managed_policy_name(
            #         "AmazonAPIGatewayInvokeFullAccess"
            #     ),
            # ],
        )
        query_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["execute-api:ManageConnections"],
                resources=[
                    "arn:aws:execute-api:*:*:*/*/DELETE/@connections/*",
                    "arn:aws:execute-api:*:*:*/*/POST/@connections/*",
                ],
            )
        )
        query_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:Retrieve",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],  # Needs access to all LLMs
            )
        )
        # Add DynamoDB permissions for WebSocket session management
        query_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:DeleteItem",
                ],
                resources=[self.websocket_session_table.table_arn],
            )
        )
        # Add Cognito permissions for token verification
        query_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cognito-idp:GetUser"],
                resources=["*"],
            )
        )
        # Add Lambda invoke permissions for async streaming
        query_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[self.async_streaming_lambda.function_arn],
            )
        )

        query_lambda_role.apply_removal_policy(RemovalPolicy.DESTROY)
        return query_lambda_role

    def create_async_streaming_lambda_role(self, knowledge_base: CfnKnowledgeBase) -> iam.Role:
        """Create role for async streaming Lambda"""
        async_streaming_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-AsyncStreamingLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                )
            ],
            inline_policies={
                "s3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:GetObject", "s3:ListBucket"],
                            resources=[f"{self.bucket.bucket_arn}*"],
                        )
                    ]
                ),
            },
        )
        
        # Add API Gateway WebSocket permissions
        async_streaming_role.add_to_policy(
            iam.PolicyStatement(
                actions=["execute-api:ManageConnections"],
                resources=[
                    "arn:aws:execute-api:*:*:*/*/DELETE/@connections/*",
                    "arn:aws:execute-api:*:*:*/*/POST/@connections/*",
                ],
            )
        )
        
        # Add Bedrock permissions
        async_streaming_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:Retrieve",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        async_streaming_role.apply_removal_policy(RemovalPolicy.DESTROY)
        return async_streaming_role

    def create_query_lambda_role(self, knowledge_base: CfnKnowledgeBase) -> iam.Role:
        """Create a role that allows lambda query Bedrock KB"""
        query_lambda_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-KBQueryLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                )
            ],
        )
        # Add DynamoDB permissions for WebSocket session management
        query_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:DeleteItem",
                ],
                resources=[self.websocket_session_table.table_arn],
            )
        )
        # Add Cognito permissions for token verification
        query_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cognito-idp:GetUser"],
                resources=["*"],
            )
        )
        # Add Lambda invoke permissions for async streaming
        query_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[self.async_streaming_lambda.function_arn],
            )
        )

        query_lambda_role.apply_removal_policy(RemovalPolicy.DESTROY)
        return query_lambda_role

    def create_query_lambda(self, knowledge_base: CfnKnowledgeBase) -> _lambda:
        # Create a role that allows lambda to query knowledge base

        query_lambda = _lambda.Function(
            self,
            self.props["stack_name_base"] + "-KBQueryLambda",
            function_name=f"{self.props['stack_name_base']}-KBQueryLambda",
            description="Function for ReVIEW to query Knowledge Base with chunked WebSocket support",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="websockets.chunked_ws_handler.handler",
            code=_lambda.Code.from_asset("lambdas"),
            timeout=Duration.minutes(5),
            environment={
                "WEBSOCKET_SESSION_TABLE_NAME": self.websocket_session_table.table_name,
                "ASYNC_STREAMING_LAMBDA_NAME": self.async_streaming_lambda.function_name,
            },
            role=self.create_query_lambda_role(knowledge_base=knowledge_base),
        )

        return query_lambda

    def store_config_in_ssm(self):
        """Store frontend configuration in SSM Parameter Store."""
        # Store API Gateway URL
        ssm.StringParameter(
            self,
            "ApiUrlParam",
            parameter_name=f"/{self.props['stack_name_base']}/api-url",
            string_value=self.api.url,
            description="REST API Gateway URL for ReVIEW frontend",
        )

        # Store WebSocket API URL
        ssm.StringParameter(
            self,
            "WebSocketUrlParam",
            parameter_name=f"/{self.props['stack_name_base']}/websocket-url",
            string_value=self.web_socket_api_stage.url,
            description="WebSocket API URL for ReVIEW frontend",
        )

        # Store Cognito User Pool ID
        ssm.StringParameter(
            self,
            "CognitoPoolIdParam",
            parameter_name=f"/{self.props['stack_name_base']}/cognito-pool-id",
            string_value=self.cognito_user_pool.user_pool_id,
            description="Cognito User Pool ID for ReVIEW frontend",
        )

        # Store Cognito Client ID
        ssm.StringParameter(
            self,
            "CognitoClientIdParam",
            parameter_name=f"/{self.props['stack_name_base']}/cognito-client-id",
            string_value=self.cognito_user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID for ReVIEW frontend",
        )
