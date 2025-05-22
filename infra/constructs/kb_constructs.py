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


import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_bedrock as bedrock
from aws_cdk import (
    aws_events as events,
)
from aws_cdk import (
    aws_events_targets as targets,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import (
    aws_stepfunctions as sfn,
)
from aws_cdk import (
    aws_stepfunctions_tasks as sfn_tasks,
)
from aws_cdk.aws_bedrock import CfnDataSource, CfnKnowledgeBase
from constructs import Construct


class ReVIEWKnowledgeBaseRole(Construct):
    """Construct for Bedrock knowledge base roles"""

    def __init__(self, scope, props: dict, source_bucket: s3.Bucket, **kwargs):
        self.props = props
        construct_id = props["stack_name_base"] + "-kbrole"
        super().__init__(scope, construct_id, **kwargs)

        self.role_name = props["stack_name_base"] + "-kbrole"
        # Setup KB role
        self.setup_kb_role(source_bucket=source_bucket)

    def setup_kb_role(self, source_bucket: s3.Bucket):
        # Create KB Role
        self.kb_role = iam.Role(
            self,
            "KB_Role",
            role_name=self.role_name,
            assumed_by=iam.ServicePrincipal(
                "bedrock.amazonaws.com",
                conditions={
                    "ArnLike": {
                        "aws:SourceArn": "arn:aws:bedrock:*:*:knowledge-base/*"
                    },
                },
            ),
            inline_policies={
                "FoundationModelPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="BedrockInvokeModelStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["bedrock:InvokeModel"],
                            resources=["arn:aws:bedrock:*::foundation-model/*"],
                        )
                    ]
                ),
                "OSSPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="OpenSearchServerlessAPIAccessAllStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["aoss:APIAccessAll"],
                            resources=["arn:aws:aoss:*:*:collection/*"],
                        )
                    ]
                ),
                "S3Policy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="S3ListBucketStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["s3:ListBucket"],
                            resources=[source_bucket.bucket_arn],
                        ),
                        iam.PolicyStatement(
                            sid="S3GetObjectStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject"],
                            resources=[f"{source_bucket.bucket_arn}/*"],
                        ),
                    ]
                ),
            },
        )

        # Delete role when destroying the stack
        self.kb_role.apply_removal_policy(RemovalPolicy.DESTROY)


class ReVIEWKnowledgeBaseConstruct(Construct):
    """Construct to deploy Bedrock knowledge base on top of existing oss"""

    def __init__(
        self,
        scope,
        props: dict,
        kb_principal_role: iam.Role,
        oss_collection_arn: str,
        source_bucket: s3.Bucket,
        **kwargs,
    ):
        """Construct to deploy a knowledge base on top of existing OSS collection
        kb_principal_role is the IAM role that KB uses
        oss_collection_arn is the OSS collection ARN KB will use
        source_bucket is the s3 bucket in which files to be synced appear"""

        self.props = props
        construct_id = props["stack_name_base"] + "-kbconstruct"
        super().__init__(scope, construct_id, **kwargs)

        self.source_bucket = source_bucket
        # Create Knowledgebase
        self.knowledge_base = self.create_knowledge_base(
            kb_principal_role, oss_collection_arn
        )
        self.data_source = self.create_data_source(self.knowledge_base)

    def create_knowledge_base(
        self, kb_principal_role: iam.Role, oss_collection_arn: str
    ) -> CfnKnowledgeBase:
        cfn_kb = CfnKnowledgeBase(
            self,
            self.props["stack_name_base"] + "-kb",
            knowledge_base_configuration=CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=self.props["embedding_model_arn"]
                ),
            ),
            name=self.props["stack_name_base"] + "-kb",
            role_arn=kb_principal_role.role_arn,
            # the properties below are optional
            description=self.props["stack_name_base"] + " RAG Knowledge base",
            storage_configuration=CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=oss_collection_arn,
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        metadata_field="AMAZON_BEDROCK_METADATA",
                        text_field="AMAZON_BEDROCK_TEXT_CHUNK",
                        vector_field="bedrock-knowledge-base-default-vector",
                    ),
                    vector_index_name=self.props["oss_index_name"],
                ),
            ),
        )
        # Delete entire KB when destroying the stack
        cfn_kb.apply_removal_policy(RemovalPolicy.DESTROY)

        return cfn_kb

    def create_data_source(self, knowledge_base: CfnKnowledgeBase) -> CfnDataSource:
        kb_id = knowledge_base.attr_knowledge_base_id
        chunking_strategy = self.props["kb_chunking_strategy"]

        # TODO: allow other chunking strategies
        assert chunking_strategy == "FIXED_SIZE"

        vector_ingestion_config_variable = bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
            chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                chunking_strategy="FIXED_SIZE",
                # the properties below are optional
                fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                    max_tokens=int(self.props["kb_max_tokens"]),
                    overlap_percentage=int(self.props["kb_overlap_percentage"]),
                ),
            )
        )

        return CfnDataSource(
            self,
            self.props["stack_name_base"] + "-RagDataSource",
            data_source_configuration=CfnDataSource.DataSourceConfigurationProperty(
                s3_configuration=CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=self.source_bucket.bucket_arn,
                    # Only documents under transcripts-txt are indexed into KB
                    inclusion_prefixes=[self.props["s3_text_transcripts_prefix"]],
                ),
                type="S3",
            ),
            knowledge_base_id=kb_id,
            name=self.props["stack_name_base"] + "-RAGDataSource",
            # RETAIN and DELETE are allowed, DELETE prevents stack from successfully
            # removing this data source on cdk destroy... not sure why. Bug?
            data_deletion_policy="DELETE",
            description=self.props["stack_name_base"] + " RAG DataSource",
            vector_ingestion_configuration=vector_ingestion_config_variable,
        )


class ReVIEWKnowledgeBaseSyncConstruct(Construct):
    """Construct to handle syncing of knowledge base (w/ polling for status)
    ddb_lambda is provided because KB sync step functions invoke a lambda to store
            job status in a dynamo table
    """

    def __init__(
        self,
        scope,
        props: dict,
        knowledge_base: CfnKnowledgeBase,
        data_source: CfnDataSource,
        source_bucket: s3.Bucket,
        ddb_lambda: _lambda.Function,
        **kwargs,
    ):
        self.props = props
        construct_id = props["stack_name_base"] + "-kbsyncconstruct"
        super().__init__(scope, construct_id, **kwargs)

        self.ddb_handler_lambda = ddb_lambda
        self.source_bucket = source_bucket

        # Create ingest lambda
        self.ingest_lambda = self.create_ingest_lambda(knowledge_base, data_source)

        # Create delete lambda
        self.deletion_lambda = self.create_deletion_lambda(knowledge_base, data_source)

        # Create job status polling lambda
        self.job_status_lambda = self.create_job_status_lambda(
            knowledge_base, data_source
        )

        # Create a state machine (Step Functions) to ingest and poll for status
        self.sync_state_machine = self.create_sync_state_machine(
            ingest_lambda=self.ingest_lambda, job_status_lambda=self.job_status_lambda
        )

        # Set up s3 to launch state machine when new files appear (w/ EventBridge)
        self.setup_events(source_bucket)

    def create_ingest_lambda_role(self, knowledge_base: CfnKnowledgeBase) -> iam.Role:
        """Create a role that allows lambda to start ingestion job"""
        ingest_lambda_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-IngestLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                ),
            ],
        )
        ingest_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:IngestKnowledgeBaseDocuments",
                    "bedrock:StartIngestionJob",
                ],
                resources=[knowledge_base.attr_knowledge_base_arn],
            )
        )
        # Allow lambda to invoke the dynamodb handling lambda for job status updates etc
        ingest_lambda_role.add_to_policy(
            statement=iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[self.ddb_handler_lambda.function_arn],
            )
        )

        ingest_lambda_role.apply_removal_policy(RemovalPolicy.DESTROY)
        return ingest_lambda_role

    def create_ingest_lambda(
        self,
        knowledge_base: CfnKnowledgeBase,
        data_source: CfnDataSource,
    ) -> _lambda:
        self.ingest_lambda_log_group = logs.LogGroup(
            self,
            "KBIngestLambdaLogGroup",
            log_group_name=f"""/aws/lambda/{self.props["stack_name_base"]}-IngestionJob""",
            removal_policy=RemovalPolicy.DESTROY,
        )
        """Create a lambda function to launch knowledge base sync and save sync job ID to dynamodb"""
        ingest_lambda = _lambda.Function(
            self,
            self.props["stack_name_base"] + "-IngestionJob",
            description="ReVIEW KB Ingestion Job Launch",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="kb.kb-ingest-job-lambda.lambda_handler",
            code=_lambda.Code.from_asset("lambdas"),
            timeout=Duration.minutes(5),
            environment=dict(
                KNOWLEDGE_BASE_ID=knowledge_base.attr_knowledge_base_id,
                DATA_SOURCE_ID=data_source.attr_data_source_id,
                DDB_LAMBDA_NAME=self.ddb_handler_lambda.function_name,
                S3_BUCKET=self.source_bucket.bucket_name,
                TEXT_TRANSCRIPTS_PREFIX=self.props["s3_text_transcripts_prefix"],
            ),
            role=self.create_ingest_lambda_role(knowledge_base),
        )

        return ingest_lambda

    def create_job_status_lambda_role(
        self, knowledge_base: CfnKnowledgeBase
    ) -> iam.Role:
        """Create a role that allows lambda to poll knowledge base ingestion job status"""
        job_status_lambda_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-IngestJobStatusLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                ),
                # TODO: reduce access to only the ddb table this application uses
                # DDB access needed because this lambda updates job statuses
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonDynamoDBFullAccess"
                ),
            ],
            inline_policies={
                "S3Write": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:GetObject"],
                            resources=[
                                f"{self.source_bucket.bucket_arn}/*",
                            ],
                        )
                    ]
                )
            },
        )
        job_status_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:GetKnowledgeBaseDocuments",
                    "bedrock:GetIngestionJob",
                ],
                resources=[knowledge_base.attr_knowledge_base_arn],
            )
        )

        # Allow lambda to invoke the dynamodb handling lambda for job status updates etc
        job_status_lambda_role.add_to_policy(
            statement=iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[self.ddb_handler_lambda.function_arn],
            )
        )

        job_status_lambda_role.apply_removal_policy(RemovalPolicy.DESTROY)
        return job_status_lambda_role

    def create_job_status_lambda(
        self, knowledge_base: CfnKnowledgeBase, data_source: CfnDataSource
    ) -> _lambda:
        """Create a lambda function to poll a knowledge base job status"""
        # Create a new Lambda function to check job status
        return _lambda.Function(
            self,
            f"{self.props['stack_name_base']}-JobStatusChecker",
            description="ReVIEW KB Ingestion Job Status Checker",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="kb.kb-job-status-lambda.lambda_handler",
            code=_lambda.Code.from_asset("lambdas"),
            timeout=Duration.minutes(1),
            environment={
                "KNOWLEDGE_BASE_ID": knowledge_base.attr_knowledge_base_id,
                "DDB_LAMBDA_NAME": self.ddb_handler_lambda.function_name,
                "DATA_SOURCE_ID": data_source.attr_data_source_id,
                "S3_BUCKET": self.source_bucket.bucket_name,
                "TEXT_TRANSCRIPTS_PREFIX": self.props["s3_text_transcripts_prefix"],
            },
            role=self.create_job_status_lambda_role(knowledge_base),
        )

    def create_sync_state_machine(
        self, ingest_lambda: _lambda, job_status_lambda: _lambda
    ) -> sfn.StateMachine:
        """State machine to submit a sync request then poll the status until complete"""

        submit_job_task = sfn_tasks.LambdaInvoke(
            self,
            "SubmitKBSyncJob",
            lambda_function=ingest_lambda,
            output_path="$.Payload",
        )

        check_job_status_task = sfn_tasks.LambdaInvoke(
            self,
            "CheckKBSyncJobStatus",
            lambda_function=job_status_lambda,
            input_path="$",
            output_path="$.Payload",
        )

        wait_state = sfn.Wait(
            self, "Wait30Seconds", time=sfn.WaitTime.duration(Duration.seconds(30))
        )

        job_failed = sfn.Fail(
            self,
            "KBSyncJobFailed",
            cause="Knowledge Base sync job failed",
            error="Job failure",
        )

        job_succeeded = sfn.Succeed(
            self,
            "KBSyncJobSucceeded",
            comment="Knowledge Base sync job completed successfully",
        )

        # Define the state machine
        chain = submit_job_task.next(check_job_status_task).next(
            sfn.Choice(self, "JobComplete?")
            .when(sfn.Condition.string_equals("$.status", "FAILED"), job_failed)
            .when(sfn.Condition.string_equals("$.status", "INDEXED"), job_succeeded)
            .otherwise(wait_state.next(check_job_status_task))
        )

        return sfn.StateMachine(
            self,
            f"{self.props['stack_name_base']}-SyncStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            # Adding lambda versions into state machine name will trigger re-deploying state machine if lambda code changes
            state_machine_name=f"{self.props['stack_name_base']}-SyncStateMachine-{ingest_lambda.current_version.version}-{job_status_lambda.current_version.version}",
            timeout=Duration.hours(1),  # TODO: timeout should update ddb status
        )

    def create_deletion_lambda_role(self, knowledge_base: CfnKnowledgeBase) -> iam.Role:
        """Create a role that allows lambda to start ingestion job"""
        deletion_lambda_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-KBDeletionLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                ),
            ],
            inline_policies={
                "DeleteFromBucket": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "s3:DeleteObject",
                                "s3:GetObject",
                                "s3:ListBucket",
                            ],
                            resources=[f"{self.source_bucket.bucket_arn}*"],
                        )
                    ]
                ),
            },
        )
        deletion_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:DeleteKnowledgeBaseDocuments",
                    "bedrock:StartIngestionJob",
                ],
                resources=[knowledge_base.attr_knowledge_base_arn],
            )
        )

        # Allow lambda to invoke the dynamodb handling lambda for job status updates etc
        deletion_lambda_role.add_to_policy(
            statement=iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[self.ddb_handler_lambda.function_arn],
            )
        )

        deletion_lambda_role.apply_removal_policy(RemovalPolicy.DESTROY)
        return deletion_lambda_role

    def create_deletion_lambda(
        self,
        knowledge_base: CfnKnowledgeBase,
        data_source: CfnDataSource,
    ) -> _lambda:
        self.kb_deletion_lambda_log_group = logs.LogGroup(
            self,
            "KBDeletionLambdaLogGroup",
            log_group_name=f"""/aws/lambda/{self.props["stack_name_base"]}-KBDeletionJob""",
            removal_policy=RemovalPolicy.DESTROY,
        )
        """Create a lambda function to launch knowledge base deletion"""
        deletion_lambda = _lambda.Function(
            self,
            self.props["stack_name_base"] + "-KBDeletionJob",
            description="ReVIEW KB Deletion Job Launch",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="kb.kb-remove-job-lambda.lambda_handler",
            code=_lambda.Code.from_asset("lambdas"),
            timeout=Duration.minutes(5),
            environment=dict(
                KNOWLEDGE_BASE_ID=knowledge_base.attr_knowledge_base_id,
                DATA_SOURCE_ID=data_source.attr_data_source_id,
                S3_BUCKET=self.source_bucket.bucket_name,
                RECORDINGS_PREFIX=self.props["s3_recordings_prefix"],
                TRANSCRIPTS_PREFIX=self.props["s3_transcripts_prefix"],
                TEXT_TRANSCRIPTS_PREFIX=self.props["s3_text_transcripts_prefix"],
                DDB_LAMBDA_NAME=self.ddb_handler_lambda.function_name,
                BDA_RECORDINGS_PREFIX=self.props["s3_bda_recordings_prefix"],
                BDA_TEXT_OUTPUT_PREFIX=self.props["s3_bda_processed_output_prefix"],
            ),
            role=self.create_deletion_lambda_role(knowledge_base),
        )

        return deletion_lambda

    def setup_events(self, source_bucket: s3.Bucket):
        """Transcripts appearing in s3 trigger the sync state machine to begin"""
        # Create event notification to the bucket for lambda functions
        # When an s3:ObjectCreated:* event happens in the bucket, the
        # state machine should be launched
        # Note the s3 bucket has event_bridge_enabled=True so it sends notifications to EB
        # Trigger when metadata file appears, as currently this shows up last

        # Create an EventBridge rule to listen for specific EB notifications
        rule = events.Rule(
            self,
            f"{self.props['stack_name_base']}-S3EventRule",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {"name": [source_bucket.bucket_name]},
                    "object": {
                        "key": [
                            {
                                "wildcard": f"{self.props['s3_text_transcripts_prefix']}/*.metadata.json"
                            }
                        ]
                    },
                },
            ),
        )

        # Add the state machine as a target for the rule
        rule.add_target(targets.SfnStateMachine(self.sync_state_machine))
