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
from aws_cdk import Duration, RemovalPolicy, NestedStack, Aspects
from constructs import Construct

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
                            ],
                        )
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
                            resources=[self.dynamodb_table.table_arn],
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
            },
            timeout=Duration.seconds(15),
            role=self.ddb_lambda_execution_role,
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
            timeout=Duration.seconds(15),
            role=self.backend_lambda_execution_role,
        )

        self.postprocess_transcript_lambda.add_permission(
            "PostProcessSTranscriptionInvokePermission",
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
                "TEXT_TRANSCRIPTS_PREFIX": self.props["s3_text_transcripts_prefix"],
            },
            timeout=Duration.seconds(30),
            role=self.presigned_url_lambda_role,
        )

        # Lambda to retrieve and optionally translate subtitles
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
            },
            timeout=Duration.minutes(2),
            role=self.subtitle_lambda_role,
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
        # Event to convert vtt transcript to txt file once it lands in s3
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.postprocess_transcript_lambda),
            s3.NotificationKeyFilter(
                prefix=f"{self.props['s3_transcripts_prefix']}/",
                suffix=".vtt",
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
