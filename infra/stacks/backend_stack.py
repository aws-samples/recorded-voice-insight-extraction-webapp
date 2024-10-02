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
import aws_cdk.aws_lambda as aws_lambda
import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_notifications as s3n
from aws_cdk import Duration, RemovalPolicy, Stack, Aspects
from constructs import Construct

# from .frontend_stack import ReVIEWFrontendStack
# from .rag_stack import ReVIEWKnowledgeBaseRoleStack, ReVIEWKnowledgeBaseStack
# from .oss_stack import ReVIEWOSSStack
import cdk_nag

"""
ReVIEW Backend CFN Stack Definition
"""


class ReVIEWBackendStack(Stack):
    """Backend of ReVIEW Application, including:
        transcription, s3 buckets, dynamodb, lambdas

    Note: `cdk destroy` will wipe everything (s3, dynamo, etc), but will
    NOT delete the Cognito user pool. Delete it in console if you wish.
    `cdk deploy` checks if a user pool with that name exists before
    creating a new one."""

    def __init__(self, scope: Construct, props: dict, **kwargs) -> None:
        self.props = props
        construct_id = props["stack_name_base"] + "-backend"

        super().__init__(scope, construct_id, **kwargs)

        # The order of these matters, later ones refer to class variables
        # instantiated in previous
        self.setup_logging()
        self.setup_roles()
        self.setup_buckets()
        self.setup_dynamodb()
        self.setup_lambdas()
        self.setup_events()

        # # Deploy knowledge base role stack
        # self.deploy_kb_role()

        # # Deploy opensearch serverless infra stack
        # self.deploy_oss()

        # # Deploy knowledge base stack
        # self.deploy_kb()

        # # Deploy nested frontend stack
        # self.deploy_frontend()

        # Attach cdk_nag to ensure AWS Solutions security level
        # Uncomment to check stack security before deploying
        # self.setup_cdk_nag()

    def setup_logging(self):
        self.generateMediaTranscriptLogGroup = logs.LogGroup(
            self,
            "GenerateMediaTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.props['unique_stack_name']}-GenerateMediaTranscript""",
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.postProcessTranscriptLogGroup = logs.LogGroup(
            self,
            "PostProcessSTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.props['unique_stack_name']}-PostProcessSTranscript""",
            removal_policy=RemovalPolicy.DESTROY,
        )

    def setup_roles(self):
        # AWS transcribe access, s3 access, etc
        self.reviewLambdaExecutionRole = iam.Role(
            self,
            f"{self.props['unique_stack_name']}-ReVIEWLambdaExecutionRole",
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
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonDynamoDBFullAccess"
                ),
            ],
            inline_policies={
                "S3Write": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:PutObject"],
                            resources=[
                                f"arn:aws:s3:::{self.props['s3_bucket_name']}/{self.props['s3_transcripts_prefix']}/*",
                                f"arn:aws:s3:::{self.props['s3_bucket_name']}/{self.props['s3_text_transcripts_prefix']}/*",
                            ],
                        )
                    ]
                ),
            },
        )

        self.reviewLambdaExecutionRole.apply_removal_policy(RemovalPolicy.DESTROY)

    def setup_buckets(self):
        self.loggingBucket = s3.Bucket(
            self,
            f"{self.props['unique_stack_name']}-LoggingBucket",
            bucket_name=f"{self.props['s3_logging_bucket_name']}",
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
            f"{self.props['unique_stack_name']}-Bucket",
            bucket_name=self.props["s3_bucket_name"],
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            versioned=True,
            server_access_logs_bucket=self.loggingBucket,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
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

    def setup_lambdas(self):
        self.generateMediaTranscript = aws_lambda.Function(
            self,
            f"{self.props['unique_stack_name']}-GenerateMediaTranscript",
            description=f"Stack {self.props['unique_stack_name']} Function GenerateMediaTranscript",
            function_name=f"{self.props['unique_stack_name']}-GenerateMediaTranscript",
            handler="generate-transcript-lambda.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=aws_lambda.Code.from_asset("lambdas/lambdas.zip"),
            environment={
                "DESTINATION_PREFIX": self.props["s3_transcripts_prefix"],
                "S3_BUCKET": f"{self.props['s3_bucket_name']}",
                "SOURCE_PREFIX": self.props["s3_recordings_prefix"],
                "DYNAMO_TABLE_NAME": self.props["ddb_table_name"],
            },
            timeout=Duration.seconds(15),
            role=self.reviewLambdaExecutionRole,
        )

        self.generateMediaTranscript.add_permission(
            "GenerateMediaTranscriptionInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
            source_account=self.props["account_id"],
        )

        self.postProcessTranscript = aws_lambda.Function(
            self,
            f"{self.props['unique_stack_name']}-PostProcessSTranscript",
            description=f"Stack {self.props['unique_stack_name']} Function PostProcessSTranscript",
            function_name=f"{self.props['unique_stack_name']}-PostProcessSTranscript",
            handler="postprocess-transcript-lambda.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=aws_lambda.Code.from_asset("lambdas/lambdas.zip"),
            environment={
                "DESTINATION_PREFIX": self.props["s3_text_transcripts_prefix"],
                "S3_BUCKET": self.props["s3_bucket_name"],
                "SOURCE_PREFIX": self.props["s3_transcripts_prefix"],
                "DYNAMO_TABLE_NAME": self.props["ddb_table_name"],
            },
            timeout=Duration.seconds(15),
            role=self.reviewLambdaExecutionRole,  # Reuse existing lambda role
        )

        self.postProcessTranscript.add_permission(
            "PostProcessSTranscriptionInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
            source_account=self.props["account_id"],
        )

        ## This creates a sev2 ticket
        # self.generateMediaTranscript.grant_invoke(
        #     iam.ServicePrincipal("s3.amazonaws.com")
        # )

    def setup_events(self):
        # Create event notification to the bucket for lambda functions
        # When an s3:ObjectCreated:* event happens in the bucket, the
        # generateMediaTranscript function should be called, with the
        # logging configuration pointing towards destinationBucketName
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.generateMediaTranscript),
            s3.NotificationKeyFilter(prefix=f"{self.props['s3_recordings_prefix']}/"),
        )
        # Event to convert json transcript to txt file once it lands in s3
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.postProcessTranscript),
            s3.NotificationKeyFilter(
                prefix=f"{self.props['s3_transcripts_prefix']}/",
                suffix=".json",
            ),
        )

    def setup_dynamodb(self):
        # Create a table to store application metadata
        # The partition key will be the username, with a sort key UUID
        # Maybe this is suboptimal? Perhaps global or secondary index is better?
        # https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_dynamodb/Table.html

        self.dynamodb_table = dynamodb.Table(
            self,
            f"{self.props['unique_stack_name']}-DDBTable-ID",
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

    # def deploy_frontend(self):
    #     self.frontend_stack = ReVIEWFrontendStack(
    #         self,
    #         f"{self.props['unique_stack_name']}-fe",
    #         backend_props=self.props,
    #     )

    # def deploy_kb_role(self):
    #     self.kb_role_stack = ReVIEWKnowledgeBaseRoleStack(
    #         self,
    #         f"{self.props['unique_stack_name']}-kb-role",
    #         backend_props=self.props,
    #     )

    # def deploy_oss(self):
    #     self.oss_stack = ReVIEWOSSStack(
    #         self,
    #         f"{self.props['unique_stack_name']}-oss",
    #         backend_props=self.props,
    #     )

    # def deploy_kb(self):
    #     self.kb_stack = ReVIEWKnowledgeBaseStack(
    #         self,
    #         f"{self.props['unique_stack_name']}-kb",
    #         backend_props=self.props,
    #     )

    def setup_cdk_nag(self):
        """Use this function to enable cdk_nag package to block deployment of possibly insecure stack elements"""
        # Attach cdk_nag to ensure AWS Solutions security level
        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.reviewLambdaExecutionRole,
            suppressions=[
                {"id": "AwsSolutions-IAM4", "reason": "Managed policies ok"},
                {"id": "AwsSolutions-IAM5", "reason": "Wildcard ok"},
            ],
        )
