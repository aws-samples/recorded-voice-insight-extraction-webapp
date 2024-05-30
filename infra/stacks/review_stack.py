import aws_cdk as cdk
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as aws_lambda
import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_notifications as s3n
from aws_cdk import Duration, RemovalPolicy, Stack
from constructs import Construct
from .frontend_stack import ReVIEWFrontendStack
import re

"""
ReVIEW CFN Stack Definition
"""


class ReVIEWStack(Stack):
    """Backend of ReVIEW Application
    Note: `cdk destroy` will wipe everything (s3, dynamo, etc), but will
    NOT delete the Cognito user pool. Delete it in console if you wish.
    `cdk deploy` checks if a user pool with that name exists before
    creating a new one."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Ensure stack name is only numbers, letters, and hyphens
        assert re.match(
            r"^[a-zA-Z0-9-]+$", construct_id
        ), "Stack name must only contain numbers, letters, and/or hyphens"

        self.stack_name_lower = construct_id.lower()
        # Applying default props
        self.props = {
            "s3BucketName": f"{self.stack_name_lower}-assets",
            "s3LoggingBucketName": f"{self.stack_name_lower}-logs",
            # Where recordings are uploaded
            "s3RecordingsPrefix": "recordings",
            # Where .json transcripts get dumped
            "s3TranscriptsPrefix": "transcripts",
            # Where .txt transcripts get dumped
            "s3TextTranscriptsPrefix": "transcripts-txt",
            # Name of dynamo DB app table
            "DDBTableName": f"{self.stack_name_lower}-app-table",
        }

        # The order of these matters, later ones refer to class variables
        # instantiated in previous
        self.setup_logging()
        self.setup_roles()
        self.setup_buckets()
        self.setup_dynamodb()
        self.setup_lambdas()
        self.setup_events()

        # Deploy nested frontend stack
        self.deploy_frontend()

    def setup_logging(self):
        self.generateMediaTranscriptLogGroup = logs.LogGroup(
            self,
            "GenerateMediaTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.stack_name_lower}-GenerateMediaTranscript""",
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.dumpTextTranscriptLogGroup = logs.LogGroup(
            self,
            "DumpTextTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.stack_name_lower}-DumpTextTranscript""",
            removal_policy=RemovalPolicy.DESTROY,
        )

    def setup_roles(self):
        # AWS transcribe access, s3 access, etc
        self.reviewLambdaExecutionRole = iam.Role(
            self,
            f"{self.stack_name_lower}-ReVIEWLambdaExecutionRole",
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
                                f"arn:aws:s3:::{self.props['s3BucketName']}/{self.props['s3TranscriptsPrefix']}/*",
                                f"arn:aws:s3:::{self.props['s3BucketName']}/{self.props['s3TextTranscriptsPrefix']}/*",
                            ],
                        )
                    ]
                ),
            },
        )

    def setup_buckets(self):
        self.loggingBucket = s3.Bucket(
            self,
            f"{self.stack_name_lower}-LoggingBucket",
            bucket_name=f"{self.props['s3LoggingBucketName']}",
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
            f"{self.stack_name_lower}-Bucket",
            bucket_name=self.props["s3BucketName"],
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            versioned=True,
            server_access_logs_bucket=self.loggingBucket,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

    def setup_lambdas(self):
        self.generateMediaTranscript = aws_lambda.Function(
            self,
            f"{self.stack_name_lower}-GenerateMediaTranscript",
            description=f"Stack {self.stack_name_lower} Function GenerateMediaTranscript",
            function_name=f"{self.stack_name_lower}-GenerateMediaTranscript",
            handler="generate-transcript-lambda.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=aws_lambda.Code.from_asset("lambdas/lambdas.zip"),
            environment={
                "DESTINATION_PREFIX": self.props["s3TranscriptsPrefix"],
                "S3_BUCKET": f"{self.props['s3BucketName']}",
                "SOURCE_PREFIX": self.props["s3RecordingsPrefix"],
                "DYNAMO_TABLE_NAME": self.props["DDBTableName"],
            },
            timeout=Duration.seconds(15),
            role=self.reviewLambdaExecutionRole,
        )

        self.generateMediaTranscript.add_permission(
            "GenerateMediaTranscriptionInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
            source_account=self.account,
        )

        self.dumpTextTranscript = aws_lambda.Function(
            self,
            f"{self.stack_name_lower}-DumpTextTranscript",
            description=f"Stack {self.stack_name_lower} Function DumpTextTranscript",
            function_name=f"{self.stack_name_lower}-DumpTextTranscript",
            handler="convert-json-to-txt-lambda.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=aws_lambda.Code.from_asset("lambdas/lambdas.zip"),
            environment={
                "DESTINATION_PREFIX": self.props["s3TextTranscriptsPrefix"],
                "S3_BUCKET": self.props["s3BucketName"],
                "SOURCE_PREFIX": self.props["s3TranscriptsPrefix"],
                "DYNAMO_TABLE_NAME": self.props["DDBTableName"],
            },
            timeout=Duration.seconds(15),
            role=self.reviewLambdaExecutionRole,  # Reuse existing lambda role
        )

        self.dumpTextTranscript.add_permission(
            "DumpTextTranscriptionInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
            source_account=self.account,
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
            s3.NotificationKeyFilter(prefix=self.props["s3RecordingsPrefix"]),
        )
        # Event to convert json transcript to txt file once it lands in s3
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.dumpTextTranscript),
            s3.NotificationKeyFilter(
                prefix=self.props["s3TranscriptsPrefix"],
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
            f"{self.stack_name_lower}-DDBTable-ID",
            table_name=self.props["DDBTableName"],
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

    def deploy_frontend(self):
        self.frontend_stack = ReVIEWFrontendStack(
            self,
            f"{self.stack_name_lower}-streamlit",
            # env=cdk.Environment(
            #     region="us-east-1",
            # ),
            # Props are passed to frontend stack as they are needed by
            # the streamlit app (backend bucket names, table names, etc)
            backend_props=self.props,
        )
