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
            "s3BucketName": kwargs.get("s3BucketName", "meeting-auto-summarizer"),
            "s3RecordingsPrefix": kwargs.get("s3RecordingsPrefix", "recordings"),
            "s3TranscriptsPrefix": kwargs.get("s3TranscriptsPrefix", "transcripts"),
            "s3NotesPrefix": kwargs.get("s3NotesPrefix", "notes"),
        }

        # The order of these matters, later ones refer to class variables
        # instantiated in previous
        self.setup_logging()
        self.setup_roles()
        self.setup_lambdas()
        self.setup_buckets()

    def setup_logging(self):
        self.generateMeetingTranscriptLogGroup = logs.CfnLogGroup(
            self,
            "GenerateMeetingTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.stack_name}-GenerateMeetingTranscript""",
        )

        self.loggingBucket = s3.CfnBucket(
            self,
            "LoggingBucket",
            access_control="LogDeliveryWrite",
            ownership_controls={
                "rules": [
                    {
                        "objectOwnership": "ObjectWriter",
                    },
                ],
            },
            bucket_encryption={
                "serverSideEncryptionConfiguration": [
                    {
                        "serverSideEncryptionByDefault": {
                            "sseAlgorithm": "aws:kms",
                            "kmsMasterKeyId": "alias/aws/s3",
                        },
                    },
                ],
            },
            public_access_block_configuration={
                "ignorePublicAcls": True,
                "restrictPublicBuckets": True,
                "blockPublicAcls": True,
                "blockPublicPolicy": True,
            },
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

        self.generateMeetingTranscript.grant_invoke(
            iam.AnyPrincipal(),
        )

    def setup_buckets(self):
        bucket = s3.Bucket(
            self,
            "MeetingAutoSummarizerBucket",
            bucket_name=f"{self.props['s3BucketName']}",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            versioned=True,
            server_access_logs_bucket=self.loggingBucket,
            removal_policy=RemovalPolicy.DESTROY,  # Create snapshot of bucket before removing ig
        )

        # Create empty subfolders in the s3 bucket
        # subdir_keys = ["s3RecordingsPrefix", "s3TranscriptsPrefix", "s3NotesPrefix"]
        # for subdir_key in subdir_keys:
        #     asset = s3_assets.Asset(self, f"{subdir_key}Asset", path=f"./{subdir_key}")
        # bucket.addObject(f"{props[subdir_key]}/")
        # bucket.put_object(f"{props[subdir_key]}/")

        # Create event notification to the bucket for lambda functions
        # When an s3:ObjectCreated:* event happens in the bucket, the
        # generateMeetingTranscript function should be called, with the
        # logging configuration pointing towards destinationBucketName
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.generateMeetingTranscript),
        )
