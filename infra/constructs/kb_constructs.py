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


# Heavy inspo from here:
# https://github.com/aws-samples/amazon-bedrock-samples/tree/main/knowledge-bases/features-examples/04-infrastructure/e2e_rag_using_bedrock_kb_cdk
from constructs import Construct
from aws_cdk import (
    Duration,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)

from aws_cdk import aws_bedrock as bedrock

from aws_cdk.aws_bedrock import CfnKnowledgeBase, CfnDataSource


class ReVIEWKnowledgeBaseRole(Construct):
    """Construct for Bedrock knowledge base roles"""

    def __init__(self, scope, props: dict, **kwargs):
        self.props = props
        construct_id = self.props["kb_role_name"]
        super().__init__(scope, construct_id, **kwargs)

        # Setup KB role
        self.setup_kb_role()

    def setup_kb_role(self):
        # Create KB Role
        self.kb_role = iam.Role(
            self,
            "KB_Role",
            role_name=self.props["kb_role_name"],
            assumed_by=iam.ServicePrincipal(
                "bedrock.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": self.props["account_id"]},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{self.props['region_name']}:{self.props['account_id']}:knowledge-base/*"
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
                            resources=[
                                f"arn:aws:bedrock:{self.props['region_name']}::foundation-model/*"
                            ],
                        )
                    ]
                ),
                "OSSPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="OpenSearchServerlessAPIAccessAllStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["aoss:APIAccessAll"],
                            resources=[
                                f"arn:aws:aoss:{self.props['region_name']}:{self.props['account_id']}:collection/*"
                            ],
                        )
                    ]
                ),
                "S3Policy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="S3ListBucketStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["s3:ListBucket"],
                            resources=[self.props["s3_bucket_arn"]],
                        ),
                        iam.PolicyStatement(
                            sid="S3GetObjectStatement",
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject"],
                            resources=[f"{self.props['s3_bucket_arn']}/*"],
                        ),
                    ]
                ),
            },
        )


class ReVIEWKnowledgeBaseConstruct(Construct):
    """Construct to deploy Bedrock knowledge base on top of existing oss"""

    def __init__(
        self,
        scope,
        props: dict,
        kb_principal_role: iam.Role,
        oss_collection_arn: str,
        **kwargs,
    ):
        """Construct to deploy a knowledge base on top of existing OSS collection"""

        self.props = props
        construct_id = props["stack_name_base"] + "-kbconstruct"
        super().__init__(scope, construct_id, **kwargs)

        self.props = props

        #   Create Knowledgebase
        self.knowledge_base = self.create_knowledge_base(
            kb_principal_role, oss_collection_arn
        )
        self.data_source = self.create_data_source(self.knowledge_base)

        # # Create ingest and query lambdas
        # self.ingest_lambda = self.create_ingest_lambda(
        #     self.knowledge_base, self.data_source
        # )
        # self.query_lambda = self.create_query_lambda(self.knowledge_base)

    def create_knowledge_base(
        self, kb_principal_role: iam.Role, oss_collection_arn: str
    ) -> CfnKnowledgeBase:
        return CfnKnowledgeBase(
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
                    bucket_arn=self.props["s3_bucket_arn"],
                    # Only documents under transcripts-txt are indexed into KB
                    inclusion_prefixes=[self.props["s3_transcripts_prefix"]],
                ),
                type="S3",
            ),
            knowledge_base_id=kb_id,
            name=self.props["stack_name_base"] + "-RAGDataSource",
            description=self.props["stack_name_base"] + " RAG DataSource",
            vector_ingestion_configuration=vector_ingestion_config_variable,
        )

    def create_ingest_lambda(
        self, knowledge_base: CfnKnowledgeBase, data_source: CfnDataSource
    ) -> lambda_:
        # Create a role that allows lambda to start ingestion job
        self.ingestLambdaRole = iam.Role(
            self,
            f"{self.props['stack_name_base']}-IngestLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        self.ingestLambdaRole.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:StartIngestionJob"],
                resources=[knowledge_base.attr_knowledge_base_arn],
            )
        )

        ingest_lambda = lambda_.Function(
            self,
            self.props["stack_name_base"] + "-IngestionJob",
            description="Function for ReVIEW Knowledge Base Ingestion and sync",
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler="kb-ingest-job-lambda.lambda_handler",
            code=lambda_.Code.from_asset("lambdas/lambdas.zip"),
            timeout=Duration.minutes(5),
            environment=dict(
                KNOWLEDGE_BASE_ID=knowledge_base.attr_knowledge_base_id,
                DATA_SOURCE_ID=data_source.attr_data_source_id,
            ),
            role=self.ingestLambdaRole,
        )

        return ingest_lambda

    def create_query_lambda(self, knowledge_base: CfnKnowledgeBase) -> lambda_:
        # Create a role that allows lambda to query knowledge base
        self.queryLambdaRole = iam.Role(
            self,
            f"{self.stack_name_lower}-ReVIEWqueryLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess"
                )
            ],
        )

        query_lambda = lambda_.Function(
            self,
            self.props["stack_name_base"] + "-KBQueryLambda",
            description="Function for ReVIEW to query Knowledge Base",
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler="kb-query-lambda.handler",
            code=lambda_.Code.from_asset("lambdas/lambdas.zip"),
            timeout=Duration.minutes(5),
            environment={
                "KNOWLEDGE_BASE_ID": knowledge_base.attr_knowledge_base_id,
                "LLM_ARN": self.backend_props["llmModelArn"],
            },
            role=self.queryLambdaRole,
        )
        # _fn_url = query_lambda.add_function_url(
        #     auth_type=lambda_.FunctionUrlAuthType.NONE,
        #     invoke_mode=lambda_.InvokeMode.BUFFERED,
        #     cors={
        #         "allowed_origins": ["*"],
        #         "allowed_methods": [lambda_.HttpMethod.POST],
        #     },
        # )

        # query_lambda.add_to_role_policy(
        #     iam.PolicyStatement(
        #         actions=[
        #             "bedrock:RetrieveAndGenerate",
        #             "bedrock:Retrieve",
        #             "bedrock:InvokeModel",
        #         ],
        #         resources=["*"],
        #     )
        # )

        return query_lambda
