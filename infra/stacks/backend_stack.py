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

import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_notifications as s3n
import aws_cdk.custom_resources as cr
from aws_cdk import Duration, RemovalPolicy, NestedStack, Aspects
from constructs import Construct
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
import json

import cdk_nag

"""
ReVIEW Backend CFN Stack Definition
"""


class ReVIEWBackendStack(NestedStack):
    """Backend of ReVIEW Application, including:
        transcription, s3 buckets, dynamodb, lambdas

    Note: `cdk destroy` will wipe everything in the backend, but will
    NOT delete the Cognito user pool. Delete it in console if you wish.
    `cdk deploy` checks if a user pool with that name exists before
    creating a new one."""

    def __init__(self, scope: Construct, props: dict, **kwargs) -> None:
        self.props = props
        construct_id = props["stack_name_base"] + "-backend"
        description = "ReVIEW Application - Backend stack"

        super().__init__(scope, construct_id, description=description, **kwargs)

        # The order of these matters, later ones refer to class variables
        # instantiated in previous
        self.setup_logging()
        self.setup_buckets()
        self.setup_dynamodb()
        self.setup_roles()
        self.setup_lambdas()
        self.setup_events()
        self.setup_default_templates_population()

        # Attach cdk_nag to ensure AWS Solutions security level
        # Uncomment to check stack security before deploying
        # self.setup_cdk_nag()

    def setup_logging(self):
        self.generate_media_transcript_lambdaLogGroup = logs.LogGroup(
            self,
            "GenerateMediaTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.props["stack_name_base"]}-GenerateMediaTranscript""",
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.postprocess_transcript_lambdaLogGroup = logs.LogGroup(
            self,
            "PostProcessTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.props["stack_name_base"]}-PostProcessTranscript""",
            removal_policy=RemovalPolicy.DESTROY,
        )

    def setup_buckets(self):
        self.loggingBucket = s3.Bucket(
            self,
            f"{self.props['stack_name_base']}-LoggingBucket",
            access_control=s3.BucketAccessControl.LOG_DELIVERY_WRITE,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        self.bucket = s3.Bucket(
            self,
            f"{self.props['stack_name_base']}-Bucket",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            versioned=True,
            server_access_logs_bucket=self.loggingBucket,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            event_bridge_enabled=True,  # EventBridge used to trigger some step functions
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.DELETE,
                        s3.HttpMethods.HEAD,
                    ],
                    allowed_origins=[
                        "*"
                    ],  # Allow all origins for presigned URL uploads
                    allowed_headers=["*"],  # Allow all headers
                    max_age=3000,  # Cache preflight response for 50 minutes
                )
            ],
        )

        # Explicitly only allow HTTPS traffic to s3 buckets
        self.loggingBucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="Allow HTTPS only to logging bucket",
                actions=["s3:*"],
                effect=iam.Effect.DENY,
                resources=[
                    self.loggingBucket.bucket_arn,
                    f"{self.loggingBucket.bucket_arn}/*",
                ],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
                principals=[iam.AnyPrincipal()],
            )
        )

        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="Allow HTTPS only to assets bucket",
                actions=["s3:*"],
                effect=iam.Effect.DENY,
                resources=[
                    self.bucket.bucket_arn,
                    f"{self.bucket.bucket_arn}/*",
                ],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
                principals=[iam.AnyPrincipal()],
            )
        )

    def setup_roles(self):
        # AWS transcribe access, s3 access, etc
        # Requires s3 bucket already created
        self.backend_lambda_execution_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-ReVIEWLambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonTranscribeFullAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonS3ReadOnlyAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                ),
            ],
            inline_policies={
                "S3Write": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:PutObject"],
                            resources=[
                                f"{self.bucket.bucket_arn}/{self.props['s3_transcripts_prefix']}/*",
                                f"{self.bucket.bucket_arn}/{self.props['s3_text_transcripts_prefix']}/*",
                                f"{self.bucket.bucket_arn}/{self.props['s3_bda_raw_output_prefix']}/*",
                                f"{self.bucket.bucket_arn}/{self.props['s3_bda_processed_output_prefix']}/*",
                            ],
                        )
                    ]
                ),
                "BedrockDataAutomation": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "bedrock:CreateDataAutomationProject",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "bedrock:CreateDataAutomationProject",
                                "bedrock:UpdateDataAutomationProject",
                                "bedrock:GetDataAutomationProject",
                                "bedrock:GetDataAutomationStatus",
                                "bedrock:ListDataAutomationProjects",
                                "bedrock:InvokeDataAutomationAsync",
                            ],
                            resources=["arn:aws:bedrock:*:*:data-automation-project/*"],
                        ),
                        iam.PolicyStatement(
                            actions=["bedrock:InvokeDataAutomationAsync"],
                            resources=[
                                "arn:aws:bedrock:*:*:data-automation-profile/us.data-automation-v1",
                            ],
                        ),
                    ]
                ),
            },
        )

        self.backend_lambda_execution_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # DDB lambda only has access to the one ddb table
        self.ddb_lambda_execution_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-ReVIEWDDBLambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                )
            ],
            inline_policies={
                "DDBLambdaPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                                "dynamodb:Scan",
                                "dynamodb:BatchGetItem",
                                "dynamodb:BatchWriteItem",
                            ],
                            resources=[
                                self.dynamodb_table.table_arn,
                                self.bda_uuid_mapping_table.table_arn,
                                self.analysis_templates_table.table_arn,
                            ],
                        )
                    ]
                )
            },
        )

        self.ddb_lambda_execution_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # Role for lambda that accesses Bedrock LLMs
        self.llm_lambda_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-LLMLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                ),
            ],
        )
        self.llm_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                ],
                resources=["*"],  # Needs access to every LLM
            )
        )

        self.llm_lambda_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # Role for lambda that generates presigned urls
        self.presigned_url_lambda_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-PresignedURLLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                )
            ],
            inline_policies={
                "S3PresignedUrl": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
                            resources=[f"{self.bucket.bucket_arn}*"],
                        )
                    ]
                ),
            },
        )

        # Role for lambda to grab and optionally translate subtitles
        self.subtitle_lambda_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-SubtitleLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                )
            ],
            inline_policies={
                "S3PresignedUrl": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:GetObject", "s3:ListBucket"],
                            resources=[f"{self.bucket.bucket_arn}*"],
                        )
                    ]
                ),
            },
        )
        # Subtitle lambda needs to access bedrock to translate subtitles to diff languages
        self.subtitle_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                ],
                resources=["*"],  # Needs access to every LLM
            )
        )

    def setup_lambdas(self):
        # Create DDB handler lambda first, as other lambdas need permission to invoke this one
        self.ddb_handler_lambda = _lambda.Function(
            self,
            f"{self.props['stack_name_base']}-DDBHandlerLambda",
            description=f"Stack {self.props['stack_name_base']} Function DDBHandlerLambda",
            function_name=f"{self.props['stack_name_base']}-DDBHandlerLambda",
            handler="ddb.ddb-handler-lambda.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "DYNAMO_TABLE_NAME": self.props["ddb_table_name"],
                "BDA_MAP_DYNAMO_TABLE_NAME": self.props["bda_map_ddb_table_name"],
                "ANALYSIS_TEMPLATES_TABLE_NAME": self.props[
                    "analysis_templates_table_name"
                ],
            },
            timeout=Duration.seconds(15),
            role=self.ddb_lambda_execution_role,
        )

        # Some lambdas need webvtt as a dependency (subtitles)
        vtt_dependency_layer = PythonLayerVersion(
            self,
            "vtt_dependency_layer",
            entry="lambda-layers/vtt-layer",  # directory containing requirements.txt for vtt lambda dependency layer
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_10,
                _lambda.Runtime.PYTHON_3_12,
            ],
            license="Apache-2.0",
            description="dependency_layer including webvtt dependency",
        )

        # Some lambdas need specific version of boto3 (BDA)
        bda_dependency_layer = PythonLayerVersion(
            self,
            "bda_dependency_layer",
            entry="lambda-layers/bda-layer",  # directory containing requirements.txt for bda lambda dependency layer
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_12,
            ],
            license="Apache-2.0",
            description="dependency_layer including specific boto3 version",
        )

        self.generate_media_transcript_lambda = _lambda.Function(
            self,
            f"{self.props['stack_name_base']}-GenerateMediaTranscript",
            description=f"Stack {self.props['stack_name_base']} Function GenerateMediaTranscript",
            function_name=f"{self.props['stack_name_base']}-GenerateMediaTranscript",
            handler="preprocessing.generate-transcript-lambda.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "DESTINATION_PREFIX": self.props["s3_transcripts_prefix"],
                "S3_BUCKET": self.bucket.bucket_name,
                "SOURCE_PREFIX": self.props["s3_recordings_prefix"],
                "DDB_LAMBDA_NAME": self.ddb_handler_lambda.function_name,
            },
            timeout=Duration.seconds(15),
            role=self.backend_lambda_execution_role,
        )

        self.generate_media_transcript_lambda.add_permission(
            "GenerateMediaTranscriptionInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
        )

        self.process_media_with_bda_lambda = _lambda.Function(
            self,
            f"{self.props['stack_name_base']}-ProcessMediaBDA",
            description=f"Stack {self.props['stack_name_base']} Function ProcessMediaBDA",
            function_name=f"{self.props['stack_name_base']}-ProcessMediaBDA",
            handler="preprocessing.generate-bda-lambda.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "DESTINATION_PREFIX": self.props["s3_bda_raw_output_prefix"],
                "S3_BUCKET": self.bucket.bucket_name,
                "DDB_LAMBDA_NAME": self.ddb_handler_lambda.function_name,
            },
            timeout=Duration.seconds(15),
            layers=[bda_dependency_layer],
            role=self.backend_lambda_execution_role,
        )

        self.process_media_with_bda_lambda.add_permission(
            "ProcessMediaWithBDAInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
        )

        self.postprocess_transcript_lambda = _lambda.Function(
            self,
            f"{self.props['stack_name_base']}-PostProcessTranscript",
            description=f"Stack {self.props['stack_name_base']} Function PostProcessTranscript",
            function_name=f"{self.props['stack_name_base']}-PostProcessTranscript",
            handler="preprocessing.postprocess-transcript-lambda.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "DESTINATION_PREFIX": self.props["s3_text_transcripts_prefix"],
                "S3_BUCKET": self.bucket.bucket_name,
                "SOURCE_PREFIX": self.props["s3_transcripts_prefix"],
                "DDB_LAMBDA_NAME": self.ddb_handler_lambda.function_name,
            },
            layers=[vtt_dependency_layer],
            timeout=Duration.seconds(15),
            role=self.backend_lambda_execution_role,
        )

        self.postprocess_transcript_lambda.add_permission(
            "PostProcessTranscriptionInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
        )

        # BDA postprocessing
        self.postprocess_bda_lambda = _lambda.Function(
            self,
            f"{self.props['stack_name_base']}-PostProcessBDA",
            description=f"Stack {self.props['stack_name_base']} Function PostProcessBDA",
            function_name=f"{self.props['stack_name_base']}-PostProcessBDA",
            handler="preprocessing.postprocess-bda-lambda.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "DESTINATION_PREFIX": self.props["s3_text_transcripts_prefix"],
                "BDA_DESTINATION_PREFIX": self.props["s3_bda_processed_output_prefix"],
                "VTT_DESTINATION_PREFIX": self.props["s3_transcripts_prefix"],
                "S3_BUCKET": self.bucket.bucket_name,
                "DDB_LAMBDA_NAME": self.ddb_handler_lambda.function_name,
            },
            layers=[vtt_dependency_layer],
            timeout=Duration.seconds(15),
            role=self.backend_lambda_execution_role,
        )

        self.postprocess_bda_lambda.add_permission(
            "PostProcessBDAInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
        )

        # Grant other lambda roles permission to invoke the ddb lambda
        self.backend_lambda_execution_role.add_to_policy(
            statement=iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[self.ddb_handler_lambda.function_arn],
            )
        )

        # Lambda to invoke Bedrock LLMs
        self.llm_lambda = _lambda.Function(
            self,
            self.props["stack_name_base"] + "-LLMLambda",
            function_name=f"{self.props['stack_name_base']}-LLMHandlerLambda",
            description="Function for ReVIEW to invoke Bedrock LLM models",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="bedrock.llm-handler-lambda.lambda_handler",
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "DDB_LAMBDA_NAME": self.ddb_handler_lambda.function_name,
                "S3_BUCKET": self.bucket.bucket_name,
                "TEXT_TRANSCRIPTS_PREFIX": self.props["s3_text_transcripts_prefix"],
            },
            timeout=Duration.minutes(5),
            role=self.llm_lambda_role,
        )

        # Lambda to generate presigned URLs for the frontend
        self.presigned_url_lambda = _lambda.Function(
            self,
            self.props["stack_name_base"] + "-PresignedURLLambda",
            function_name=f"{self.props['stack_name_base']}-PresignedURLLambda",
            description="Function for ReVIEW backend to generate presigned URLs",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="s3.presigned-url-lambda.lambda_handler",
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "S3_BUCKET": self.bucket.bucket_name,
                "RECORDINGS_PREFIX": self.props["s3_recordings_prefix"],
                "BDA_RECORDINGS_PREFIX": self.props["s3_bda_recordings_prefix"],
                "TEXT_TRANSCRIPTS_PREFIX": self.props["s3_text_transcripts_prefix"],
            },
            timeout=Duration.seconds(30),
            role=self.presigned_url_lambda_role,
        )

        self.subtitle_lambda = _lambda.Function(
            self,
            self.props["stack_name_base"] + "-SubtitleLambda",
            function_name=f"{self.props['stack_name_base']}-SubtitleLambda",
            description="Function for ReVIEW backend to retrieve and translate subtitles.",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="bedrock.subtitle-handler-lambda.lambda_handler",
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "S3_BUCKET": self.bucket.bucket_name,
                "TRANSCRIPTS_PREFIX": self.props["s3_transcripts_prefix"],
                "FOUNDATION_MODEL_ID": self.props["llm_model_id"],
            },
            layers=[vtt_dependency_layer],
            timeout=Duration.minutes(2),
            role=self.subtitle_lambda_role,
        )

        # Analysis Templates Lambda - serves analysis templates for the frontend
        self.analysis_templates_lambda = _lambda.Function(
            self,
            self.props["stack_name_base"] + "-AnalysisTemplatesLambda",
            function_name=f"{self.props['stack_name_base']}-AnalysisTemplatesLambda",
            description="Function for ReVIEW to serve analysis templates.",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="analysis.analysis-templates-lambda.lambda_handler",
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "ANALYSIS_TEMPLATES_TABLE_NAME": self.props[
                    "analysis_templates_table_name"
                ],
                "LLM_MODEL_ID": self.props["llm_model_id"],
            },
            timeout=Duration.seconds(30),
            role=self.ddb_lambda_execution_role,
        )

        # Lambda to populate default analysis templates at deployment time
        self.populate_default_templates_lambda = _lambda.Function(
            self,
            self.props["stack_name_base"] + "-PopulateDefaultTemplatesLambda",
            function_name=f"{self.props['stack_name_base']}-PopulateDefaultTemplatesLambda",
            description="Function to populate default analysis templates in DynamoDB",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="analysis.populate-default-templates-lambda.lambda_handler",
            code=_lambda.Code.from_asset("lambdas"),
            environment={
                "ANALYSIS_TEMPLATES_TABLE_NAME": self.props[
                    "analysis_templates_table_name"
                ],
            },
            timeout=Duration.seconds(60),
            role=self.ddb_lambda_execution_role,
        )

        # Create a Lambda layer with the default templates JSON file
        self.default_templates_layer = PythonLayerVersion(
            self,
            "default_templates_layer",
            entry="lambda-layers/analysis-templates-layer",  # directory containing default_analysis_templates.json
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_10,
                _lambda.Runtime.PYTHON_3_12,
            ],
            license="MIT-0",
            description="Layer containing default analysis templates JSON file",
        )

        # Add the layer to the populate templates lambda
        self.populate_default_templates_lambda.add_layers(self.default_templates_layer)

        # Add additional permissions to LLM Lambda role now that other Lambdas are created
        # Permission to invoke DDB Lambda for transcript retrieval
        self.llm_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[self.ddb_handler_lambda.function_arn],
            )
        )
        # Permission to read transcript files from S3
        self.llm_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[
                    f"{self.bucket.bucket_arn}/{self.props['s3_text_transcripts_prefix']}/*"
                ],
            )
        )

    def setup_events(self):
        # Create event notification to the bucket for lambda functions
        # When an s3:ObjectCreated:* event happens in the bucket, the
        # generate_media_transcript_lambda function should be called, with the
        # logging configuration pointing towards destinationBucketName
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.generate_media_transcript_lambda),
            s3.NotificationKeyFilter(prefix=f"{self.props['s3_recordings_prefix']}/"),
        )
        # Event to process uploaded file with BDA (Bedrock Data Automation)
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.process_media_with_bda_lambda),
            s3.NotificationKeyFilter(
                prefix=f"{self.props['s3_bda_recordings_prefix']}/"
            ),
        )
        # Event to convert vtt transcript to txt file once it lands in s3
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.postprocess_transcript_lambda),
            s3.NotificationKeyFilter(
                prefix=f"{self.props['s3_transcripts_prefix']}/",
                suffix=".vtt",
            ),
        )
        # Event to convert BDA output to vtt and txt files once it lands in s3
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.postprocess_bda_lambda),
            s3.NotificationKeyFilter(
                prefix=f"{self.props['s3_bda_raw_output_prefix']}/",
                suffix="standard_output/0/result.json",
            ),
        )

    def setup_dynamodb(self):
        # Create a table to store application metadata
        # The partition key will be the username, with a sort key UUID
        # Maybe this is suboptimal? Perhaps global or secondary index is better?
        # https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_dynamodb/Table.html

        self.dynamodb_table = dynamodb.Table(
            self,
            f"{self.props['stack_name_base']}-DDBTable-ID",
            table_name=self.props["ddb_table_name"],
            partition_key=dynamodb.Attribute(
                name="username", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="UUID", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # This table maps BDA-assigned UUID to ReVIEW-app-assigned UUID
        # Sort key is BDA-UUID, other fields are UUID and username
        self.bda_uuid_mapping_table = dynamodb.Table(
            self,
            f"{self.props['stack_name_base']}-BDAUUIDMapTable",
            table_name=self.props["bda_map_ddb_table_name"],
            partition_key=dynamodb.Attribute(
                name="BDA-UUID", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Analysis templates table to store both default and user-specific templates
        # Partition key is user_id (with "default" for built-in templates)
        # Sort key is template_id
        self.analysis_templates_table = dynamodb.Table(
            self,
            f"{self.props['stack_name_base']}-AnalysisTemplatesTable",
            table_name=self.props["analysis_templates_table_name"],
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="template_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

    def setup_default_templates_population(self):
        """Create custom resource to populate default analysis templates"""
        # Custom resource to populate default templates
        self.populate_templates_custom_resource = cr.AwsCustomResource(
            self,
            f"{self.props['stack_name_base']}-PopulateDefaultTemplates",
            on_create=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": self.populate_default_templates_lambda.function_name,
                    "Payload": json.dumps(
                        {"RequestType": "Create", "ResourceProperties": {}}
                    ),
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    "populate-default-templates"
                ),
            ),
            on_update=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": self.populate_default_templates_lambda.function_name,
                    "Payload": json.dumps(
                        {"RequestType": "Update", "ResourceProperties": {}}
                    ),
                },
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    iam.PolicyStatement(
                        actions=["lambda:InvokeFunction"],
                        resources=[self.populate_default_templates_lambda.function_arn],
                    )
                ]
            ),
        )

        # Ensure the custom resource runs after the table is created
        self.populate_templates_custom_resource.node.add_dependency(
            self.analysis_templates_table
        )

    def setup_cdk_nag(self):
        """Use this function to enable cdk_nag package to block deployment of possibly insecure stack elements"""
        # Attach cdk_nag to ensure AWS Solutions security level
        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.backend_lambda_execution_role,
            suppressions=[
                {"id": "AwsSolutions-IAM4", "reason": "Managed policies ok"},
                {"id": "AwsSolutions-IAM5", "reason": "Wildcard ok"},
            ],
        )
