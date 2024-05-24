import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as aws_lambda
import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_notifications as s3n
from aws_cdk import Duration, RemovalPolicy, Stack
from constructs import Construct

"""
ReVIEW CFN Stack Definition
"""


class ReVIEWStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Applying default props
        self.props = {
            "s3BucketName": kwargs.get("s3BucketName", "review-app-assets"),
            "s3LoggingBucketName": kwargs.get("s3LoggingBucketName", "review-app-logs"),
            # Where recordings are uploaded
            "s3RecordingsPrefix": kwargs.get("s3RecordingsPrefix", "recordings"),
            # Where .json transcripts get dumped
            "s3TranscriptsPrefix": kwargs.get("s3TranscriptsPrefix", "transcripts"),
            # Where .txt transcripts get dumped
            "s3TextTranscriptsPrefix": kwargs.get(
                "s3TextTranscriptsPrefix", "transcripts-txt"
            ),
            # # Where LLM summaries get dumped
            # "s3SummaryPrefix": kwargs.get("s3SummaryPrefix", "llm-summaries"),
            # # Which Bedrock LLM to use to generate summaries
            # "SummaryLLMID": kwargs.get(
            #     "SummaryLLMID", "anthropic.claude-3-sonnet-20240229-v1:0"
            # ),
            # Name of dynamo DB app table (PK = "UUID" hardcoded)
            "DDBTableName": kwargs.get("DDBTableName", "ReVIEW-App-Table"),
        }

        # The order of these matters, later ones refer to class variables
        # instantiated in previous
        self.setup_logging()
        self.setup_roles()
        self.setup_buckets()
        self.setup_dynamodb()
        self.setup_lambdas()
        self.setup_events()

    def setup_logging(self):
        self.generateMediaTranscriptLogGroup = logs.LogGroup(
            self,
            "GenerateMediaTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.stack_name}-GenerateMediaTranscript""",
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.dumpTextTranscriptLogGroup = logs.LogGroup(
            self,
            "DumpTextTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.stack_name}-DumpTextTranscript""",
            removal_policy=RemovalPolicy.DESTROY,
        )
        # self.generateSummaryLogGroup = logs.LogGroup(
        #     self,
        #     "GenerateSummaryLogGroup",
        #     log_group_name=f"""/aws/lambda/{self.stack_name}-GenerateSummary""",
        #     removal_policy=RemovalPolicy.DESTROY,
        # )

    def setup_roles(self):
        # AWS transcribe access, s3 access, etc
        self.masLambdaExecutionRole = iam.Role(
            self,
            "ReVIEWLambdaExecutionRole",
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
                                # f"arn:aws:s3:::{self.props['s3BucketName']}/{self.props['s3SummaryPrefix']}/*",
                            ],
                        )
                    ]
                ),
            },
        )

    def setup_buckets(self):
        self.loggingBucket = s3.Bucket(
            self,
            "ReVIEWLoggingBucket",
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
            "ReVIEWBucket",
            bucket_name=self.props["s3BucketName"],
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            versioned=True,
            server_access_logs_bucket=self.loggingBucket,
            removal_policy=RemovalPolicy.DESTROY,
        )

    def setup_lambdas(self):
        self.generateMediaTranscript = aws_lambda.Function(
            self,
            "GenerateMediaTranscript",
            description=f"Stack {self.stack_name} Function GenerateMediaTranscript",
            function_name=f"{self.stack_name}-GenerateMediaTranscript",
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
            role=self.masLambdaExecutionRole,
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
            "DumpTextTranscript",
            description=f"Stack {self.stack_name} Function DumpTextTranscript",
            function_name=f"{self.stack_name}-DumpTextTranscript",
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
            role=self.masLambdaExecutionRole,  # Reuse existing lambda role
        )

        self.dumpTextTranscript.add_permission(
            "DumpTextTranscriptionInvokePermission",
            principal=iam.ServicePrincipal("s3.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=self.bucket.bucket_arn,
            source_account=self.account,
        )

        # self.generateSummary = aws_lambda.Function(
        #     self,
        #     "GenerateSummary",
        #     description=f"Stack {self.stack_name} Function GenerateSummary",
        #     function_name=f"{self.stack_name}-GenerateSummary",
        #     handler="generate-summary-lambda.lambda_handler",
        #     runtime=aws_lambda.Runtime.PYTHON_3_12,
        #     memory_size=128,
        #     code=aws_lambda.Code.from_asset("lambdas/lambdas.zip"),
        #     environment={
        #         "DESTINATION_PREFIX": self.props["s3SummaryPrefix"],
        #         "S3_BUCKET": self.props["s3BucketName"],
        #         "SOURCE_PREFIX": self.props["s3TextTranscriptsPrefix"],
        #         "LLM_ID": self.props["SummaryLLMID"],
        #         "DYNAMO_TABLE_NAME": self.props["DDBTableName"],
        #     },
        #     timeout=Duration.seconds(60),
        #     role=self.masLambdaExecutionRole,  # Reuse existing lambda role
        # )

        # self.generateSummary.add_permission(
        #     "GenerateSummaryionInvokePermission",
        #     principal=iam.ServicePrincipal("s3.amazonaws.com"),
        #     action="lambda:InvokeFunction",
        #     source_arn=self.bucket.bucket_arn,
        #     source_account=self.account,
        # )

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
        # Event to read in txt file for LLM summary generation
        # self.bucket.add_event_notification(
        #     s3.EventType.OBJECT_CREATED,
        #     s3n.LambdaDestination(self.generateSummary),
        #     s3.NotificationKeyFilter(
        #         prefix=self.props["s3TextTranscriptsPrefix"],
        #         suffix=".txt",
        #     ),
        # )

    def setup_dynamodb(self):
        # Create a table to store application metadata
        # The partition key will be a uuid (string) named "UUID"

        self.dynamodb_table = dynamodb.Table(
            self,
            "ReVIEW-App-DDBTable-ID",
            table_name=self.props["DDBTableName"],
            partition_key=dynamodb.Attribute(
                name="UUID", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.DESTROY,
        )
