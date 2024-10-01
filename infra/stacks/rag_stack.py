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
from aws_cdk import Stack
from aws_cdk import (
    Duration,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)

from aws_cdk import aws_bedrock as bedrock

from aws_cdk.aws_bedrock import CfnKnowledgeBase, CfnDataSource
from infra.constructs.kb_constructs import ReVIEWKnowledgeBaseRole
from infra.constructs.oss_constructs import ReVIEWOSSConstruct


class ReVIEWRAGStack(Stack):
    """Stack to deploy both knowledge base and opensearch serverless"""

    def __init__(self, scope, props: dict, **kwargs):
        self.props = props
        construct_id = props["stack_name_base"] + "-rag"
        super().__init__(scope, construct_id, **kwargs)

        # Setup KB role, which will be available with name props.kb_role_name
        self.kb_role_construct = ReVIEWKnowledgeBaseRole(self, props)

        # Deploy OSS collection, with data access allowed to kb_role
        self.oss_construct = ReVIEWOSSConstruct(
            self, props, [self.kb_role_construct.kb_role]
        )


# class ReVIEWKnowledgeBaseStack(NestedStack):
#     """Stack to deploy Bedrock knowledge base"""

#     def __init__(self, scope, construct_id, backend_props: dict, **kwargs):
#         super().__init__(scope, construct_id, **kwargs)
#         # backend_props are exported as env variables in the streamlit
#         # docker container (e.g. backend bucket names, table names, etc)
#         self.backend_props = backend_props
#         self.kb_role_name = self.backend_props["stackNameLower"] + "-ReVIEWKBRole"
#         self.stack_name_lower = self.backend_props["stackNameLower"]
#         self.collection_name = self.backend_props["ossCollectionName"]
#         self.embedding_model_arn = self.backend_props["embeddingModelArn"]
#         self.index_name = self.backend_props["ossIndexName"]
#         self.chunking_strategy = self.backend_props["kbChunkingStrategy"]
#         self.max_tokens = int(self.backend_props["kbMaxTokens"])
#         self.overlap_percentage = int(self.backend_props["kbOverlapPercentage"])
#         self.s3_bucket_arn = f"arn:aws:s3:::{self.backend_props['s3BucketName']}"
#         self.s3_transcripts_prefix = self.backend_props["s3TranscriptsPrefix"]

#         self.kbRoleArn = ssm.StringParameter.from_string_parameter_attributes(
#             self,
#             f"kbRoleArn-{self.kb_role_name}",
#             parameter_name=f"kbRoleArn-{self.kb_role_name}",
#         ).string_value
#         print("kbRoleArn: " + self.kbRoleArn)
#         self.collectionArn = ssm.StringParameter.from_string_parameter_attributes(
#             self,
#             f"collectionArn-{self.collection_name}",
#             parameter_name=f"collectionArn-{self.collection_name}",
#         ).string_value
#         print("collectionArn: " + self.collectionArn)

#         #   Create Knowledgebase
#         self.knowledge_base = self.create_knowledge_base()
#         self.data_source = self.create_data_source(self.knowledge_base)

#         # Create ingest and query lambdas
#         self.ingest_lambda = self.create_ingest_lambda(
#             self.knowledge_base, self.data_source
#         )
#         self.query_lambda = self.create_query_lambda(self.knowledge_base)

#     def create_knowledge_base(self) -> CfnKnowledgeBase:
#         return CfnKnowledgeBase(
#             self,
#             self.backend_props["stackNameLower"] + "-RagKB",
#             knowledge_base_configuration=CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
#                 type="VECTOR",
#                 vector_knowledge_base_configuration=CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
#                     embedding_model_arn=self.embedding_model_arn
#                 ),
#             ),
#             name=self.backend_props["stackNameLower"] + "-KB",
#             role_arn=self.kbRoleArn,
#             # the properties below are optional
#             description=self.backend_props["stackNameLower"] + " RAG Knowledge base",
#             storage_configuration=CfnKnowledgeBase.StorageConfigurationProperty(
#                 type="OPENSEARCH_SERVERLESS",
#                 # the properties below are optional
#                 opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
#                     collection_arn=self.collectionArn,
#                     field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
#                         metadata_field="AMAZON_BEDROCK_METADATA",
#                         text_field="AMAZON_BEDROCK_TEXT_CHUNK",
#                         vector_field="bedrock-knowledge-base-default-vector",
#                     ),
#                     vector_index_name=self.index_name,
#                 ),
#             ),
#         )

#     def create_data_source(self, knowledge_base) -> CfnDataSource:
#         kbid = knowledge_base.attr_knowledge_base_id
#         chunking_strategy = self.chunking_strategy
#         if chunking_strategy == "FIXED_SIZE":
#             vector_ingestion_config_variable = bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
#                 chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
#                     chunking_strategy="FIXED_SIZE",
#                     # the properties below are optional
#                     fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
#                         max_tokens=self.max_tokens,
#                         overlap_percentage=self.overlap_percentage,
#                     ),
#                 )
#             )
#         # elif chunking_strategy == "Default chunking":
#         #     vector_ingestion_config_variable = bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
#         #         chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
#         #             chunking_strategy="FIXED_SIZE",
#         #             # the properties below are optional
#         #             fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
#         #                 max_tokens=300, overlap_percentage=20
#         #             ),
#         #         )
#         #     )
#         # else:
#         #     vector_ingestion_config_variable = bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
#         #         chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
#         #             chunking_strategy="NONE"
#         #         )
#         #     )
#         return CfnDataSource(
#             self,
#             self.backend_props["stackNameLower"] + "-RagDataSource",
#             data_source_configuration=CfnDataSource.DataSourceConfigurationProperty(
#                 s3_configuration=CfnDataSource.S3DataSourceConfigurationProperty(
#                     bucket_arn=self.s3_bucket_arn,
#                     # Only documents under transcripts-txt are indexed into KB
#                     inclusion_prefixes=[self.s3_transcripts_prefix],
#                 ),
#                 type="S3",
#             ),
#             knowledge_base_id=kbid,
#             name=self.backend_props["stackNameLower"] + "-RAGDataSource",
#             # the properties below are optional
#             description=self.backend_props["stackNameLower"] + " RAG DataSource",
#             vector_ingestion_configuration=vector_ingestion_config_variable,
#         )

#     def create_ingest_lambda(self, knowledge_base, data_source) -> lambda_:
#         # Create a role that allows lambda to start ingestion job
#         self.ingestLambdaRole = iam.Role(
#             self,
#             f"{self.stack_name_lower}-ReVIEWIngestLambdaRole",
#             assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
#         )
#         self.ingestLambdaRole.add_to_policy(
#             iam.PolicyStatement(
#                 actions=["bedrock:StartIngestionJob"],
#                 resources=[knowledge_base.attr_knowledge_base_arn],
#             )
#         )

#         ingest_lambda = lambda_.Function(
#             self,
#             self.backend_props["stackNameLower"] + "-IngestionJob",
#             description="Function for ReVIEW Knowledge Base Ingestion and sync",
#             runtime=lambda_.Runtime.PYTHON_3_10,
#             handler="kb-ingest-job-lambda.lambda_handler",
#             code=lambda_.Code.from_asset("lambdas/lambdas.zip"),
#             timeout=Duration.minutes(5),
#             environment=dict(
#                 KNOWLEDGE_BASE_ID=knowledge_base.attr_knowledge_base_id,
#                 DATA_SOURCE_ID=data_source.attr_data_source_id,
#             ),
#             role=self.ingestLambdaRole,
#         )

#         return ingest_lambda

#     def create_query_lambda(self, knowledge_base) -> lambda_:
#         # Create a role that allows lambda to query knowledge base
#         self.queryLambdaRole = iam.Role(
#             self,
#             f"{self.stack_name_lower}-ReVIEWqueryLambdaRole",
#             assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
#             managed_policies=[
#                 iam.ManagedPolicy.from_aws_managed_policy_name(
#                     "AmazonBedrockFullAccess"
#                 )
#             ],
#         )

#         query_lambda = lambda_.Function(
#             self,
#             self.backend_props["stackNameLower"] + "-KBQueryLambda",
#             description="Function for ReVIEW to query Knowledge Base",
#             runtime=lambda_.Runtime.PYTHON_3_10,
#             handler="kb-query-lambda.handler",
#             code=lambda_.Code.from_asset("lambdas/lambdas.zip"),
#             timeout=Duration.minutes(5),
#             environment={
#                 "KNOWLEDGE_BASE_ID": knowledge_base.attr_knowledge_base_id,
#                 "LLM_ARN": self.backend_props["llmModelArn"],
#             },
#             role=self.queryLambdaRole,
#         )
#         # _fn_url = query_lambda.add_function_url(
#         #     auth_type=lambda_.FunctionUrlAuthType.NONE,
#         #     invoke_mode=lambda_.InvokeMode.BUFFERED,
#         #     cors={
#         #         "allowed_origins": ["*"],
#         #         "allowed_methods": [lambda_.HttpMethod.POST],
#         #     },
#         # )

#         # query_lambda.add_to_role_policy(
#         #     iam.PolicyStatement(
#         #         actions=[
#         #             "bedrock:RetrieveAndGenerate",
#         #             "bedrock:Retrieve",
#         #             "bedrock:InvokeModel",
#         #         ],
#         #         resources=["*"],
#         #     )
#         # )

#         return query_lambda
