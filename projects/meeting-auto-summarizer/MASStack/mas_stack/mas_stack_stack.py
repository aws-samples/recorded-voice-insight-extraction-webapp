import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as aws_lambda
import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_notifications as s3n
from aws_cdk import Duration, RemovalPolicy, Stack
from constructs import Construct

"""
Meeting Auto Summarizer CFN Stack Definition
"""


class MASStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Applying default props
        self.props = {
            "s3BucketName": kwargs.get(
                "s3BucketName", "meeting-auto-summarizer-assets"
            ),
            "s3LoggingBucketName": kwargs.get(
                "s3LoggingBucketName", "meeting-auto-summarizer-logs"
            ),
            "s3RecordingsPrefix": kwargs.get("s3RecordingsPrefix", "recordings"),
            "s3TranscriptsPrefix": kwargs.get("s3TranscriptsPrefix", "transcripts"),
            "s3NotesPrefix": kwargs.get("s3NotesPrefix", "notes"),
        }

        # The order of these matters, later ones refer to class variables
        # instantiated in previous
        self.setup_logging()
        self.setup_roles()
        self.setup_buckets()
        self.setup_lambdas()

        # Create event notification to the bucket for lambda functions
        # When an s3:ObjectCreated:* event happens in the bucket, the
        # generateMeetingTranscript function should be called, with the
        # logging configuration pointing towards destinationBucketName
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.generateMeetingTranscript),
        )

    def setup_logging(self):
        self.generateMeetingTranscriptLogGroup = logs.CfnLogGroup(
            self,
            "GenerateMeetingTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.stack_name}-GenerateMeetingTranscript""",
        )

    def setup_roles(self):
        self.generateMeetingTranscriptLambdaRole = iam.Role(
            self,
            "GenerateMeetingTranscriptLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonTranscribeFullAccess"
                )
            ],
            inline_policies={
                "CreateLogGroup": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["logs:CreateLogGroup"],
                            resources=["arn:aws:logs:*:*:*"],
                        )
                    ]
                ),
                "LogsAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                            resources=[self.generateMeetingTranscriptLogGroup.attr_arn],
                        )
                    ]
                ),
                "S3RecordingsRead": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:GetObject"],
                            resources=[
                                f"arn:aws:s3:::{self.props['s3BucketName']}/{self.props['s3RecordingsPrefix']}/*"
                            ],
                        )
                    ]
                ),
                "S3TranscriptsWrite": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:PutObject"],
                            resources=[
                                f"arn:aws:s3:::{self.props['s3BucketName']}/{self.props['s3TranscriptsPrefix']}/*"
                            ],
                        )
                    ]
                ),
            },
        )

    def setup_buckets(self):
        self.loggingBucket = s3.Bucket(
            self,
            "MeetingSummarizerLoggingBucket",
            bucket_name=f"{self.props['s3LoggingBucketName']}",
            access_control=s3.BucketAccessControl.LOG_DELIVERY_WRITE,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.bucket = s3.Bucket(
            self,
            "MeetingAutoSummarizerBucket",
            bucket_name=f"{self.props['s3BucketName']}",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            versioned=True,
            server_access_logs_bucket=self.loggingBucket,
            removal_policy=RemovalPolicy.DESTROY,
        )

    def setup_lambdas(self):
        self.generateMeetingTranscript = aws_lambda.Function(
            self,
            "GenerateMeetingTranscript",
            description=f"Stack {self.stack_name} Function GenerateMeetingTranscript",
            function_name=f"{self.stack_name}-GenerateMeetingTranscript",
            handler="generate-transcript-lambda.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            memory_size=128,
            code=aws_lambda.Code.from_asset("lambdas/generate-transcript-lambda.zip"),
            environment={
                "DESTINATION_PREFIX": self.props["s3TranscriptsPrefix"],
                "S3_BUCKET": f"{self.props['s3BucketName']}",
                "SOURCE_PREFIX": self.props["s3RecordingsPrefix"],
            },
            timeout=Duration.seconds(15),
            role=self.generateMeetingTranscriptLambdaRole,
        )

        self.generateMeetingTranscript.add_permission(
            "GenerateMeetingTranscriptionInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
            source_account=self.account,
        )

        ## This creates a sev2 ticket, lol
        # self.generateMeetingTranscript.grant_invoke(
        #     iam.ServicePrincipal("s3.amazonaws.com")
        # )
