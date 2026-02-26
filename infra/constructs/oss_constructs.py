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

import json

import aws_cdk as core
from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import custom_resources as cr
from aws_cdk.aws_iam import ServicePrincipal
from aws_cdk.aws_lambda import Code, Runtime, Tracing
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_opensearchserverless import (
    CfnAccessPolicy,
    CfnCollection,
    CfnSecurityPolicy,
)
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs.vector_store_base import VectorStoreConstruct


class OSSVectorStoreConstruct(VectorStoreConstruct):
    """OpenSearch Serverless vector store implementation for Bedrock Knowledge Base."""

    def __init__(self, scope, props: dict, kb_role: iam.Role, **kwargs):
        self.props = props
        construct_id = f"{props['stack_name_base']}-oss"
        super().__init__(scope, construct_id, **kwargs)

        self.collection_name = props["oss_collection_name"]
        self.oss_lambda_role = self._create_oss_lambda_role()

        self.encryptionPolicy = self._create_encryption_policy()
        self.networkPolicy = self._create_network_policy()
        self.dataAccessPolicy = self._create_data_access_policy(
            [kb_role, self.oss_lambda_role]
        )
        self.collection = self._create_collection()

        self.networkPolicy.node.add_dependency(self.encryptionPolicy)
        self.dataAccessPolicy.node.add_dependency(self.networkPolicy)
        self.collection.node.add_dependency(self.encryptionPolicy)

        self._create_oss_index()

    @property
    def vector_store_arn(self) -> str:
        return self.collection.attr_arn

    @property
    def vector_store_type(self) -> str:
        return "OPENSEARCH_SERVERLESS"

    def _create_encryption_policy(self) -> CfnSecurityPolicy:
        policy = json.dumps(
            {
                "Rules": [
                    {
                        "Resource": [f"collection/{self.collection_name}"],
                        "ResourceType": "collection",
                    }
                ],
                "AWSOwnedKey": True,
            },
            indent=2,
        )
        pol = CfnSecurityPolicy(
            self,
            "EncryptionSecurityPolicy",
            policy=policy,
            name=f"{self.collection_name}-enc-pol"[-31:],
            type="encryption",
        )
        pol.apply_removal_policy(RemovalPolicy.DESTROY)
        return pol

    def _create_network_policy(self) -> CfnSecurityPolicy:
        policy = json.dumps(
            [
                {
                    "Description": f"Public access for {self.props['stack_name_base']} KB collection",
                    "Rules": [
                        {
                            "Resource": [f"collection/{self.collection_name}"],
                            "ResourceType": "dashboard",
                        },
                        {
                            "Resource": [f"collection/{self.collection_name}"],
                            "ResourceType": "collection",
                        },
                    ],
                    "AllowFromPublic": True,
                }
            ],
            indent=2,
        )
        pol = CfnSecurityPolicy(
            self,
            "NetworkSecurityPolicy",
            policy=policy,
            name=f"{self.collection_name}-ntw-pol"[-31:],
            type="network",
        )
        pol.apply_removal_policy(RemovalPolicy.DESTROY)
        return pol

    def _create_collection(self) -> CfnCollection:
        coll = CfnCollection(
            self,
            "OpsSearchCollection",
            name=self.collection_name,
            description="Collection for ReVIEW App search using OpenSearch Serverless",
            type="VECTORSEARCH",
        )
        coll.apply_removal_policy(RemovalPolicy.DESTROY)
        return coll

    def _create_data_access_policy(
        self, principal_roles: list[iam.Role]
    ) -> CfnAccessPolicy:
        policy = json.dumps(
            [
                {
                    "Rules": [
                        {
                            "Resource": [f"collection/{self.collection_name}"],
                            "Permission": [
                                "aoss:CreateCollectionItems",
                                "aoss:UpdateCollectionItems",
                                "aoss:DescribeCollectionItems",
                            ],
                            "ResourceType": "collection",
                        },
                        {
                            "ResourceType": "index",
                            "Resource": [f"index/{self.collection_name}/*"],
                            "Permission": [
                                "aoss:CreateIndex",
                                "aoss:DescribeIndex",
                                "aoss:ReadDocument",
                                "aoss:WriteDocument",
                                "aoss:UpdateIndex",
                                "aoss:DeleteIndex",
                            ],
                        },
                    ],
                    "Principal": [r.role_arn for r in principal_roles],
                    "Description": "ReVIEW Knowledge Base OSS data-access-rule",
                }
            ],
            indent=2,
        )
        pol = CfnAccessPolicy(
            self,
            "ReVIEWOSSDataAccessPolicy",
            name=f"{self.collection_name}"[-31:],
            description="ReVIEW OSS data access policy",
            type="data",
            policy=policy,
        )
        pol.apply_removal_policy(RemovalPolicy.DESTROY)
        return pol

    def _create_oss_lambda_role(self):
        role = iam.Role(
            self,
            "OSSLambdaRole",
            assumed_by=ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "OSSLambdaPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "aoss:*",
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            resources=["*"],
                        )
                    ]
                )
            },
        )
        role.apply_removal_policy(RemovalPolicy.DESTROY)
        return role

    def _create_oss_index(self):
        layer = PythonLayerVersion(
            self,
            "oss_dependency_layer",
            entry="lambda-layers/oss-layer",
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_8,
                _lambda.Runtime.PYTHON_3_9,
                _lambda.Runtime.PYTHON_3_10,
            ],
            license="Apache-2.0",
            description="Layer with opensearch-py and dependencies",
        )

        index_lambda = _lambda.Function(
            self,
            "ReVIEW-oss-index-creation-lambda",
            function_name=f"{self.props['oss_index_name']}-InfraSetupLambda",
            code=Code.from_asset("lambdas/oss"),
            handler="oss_handler.lambda_handler",
            description="Lambda to create OSS index for ReVIEW App",
            role=self.oss_lambda_role,
            memory_size=1024,
            timeout=Duration.minutes(14),
            runtime=Runtime.PYTHON_3_8,
            tracing=Tracing.ACTIVE,
            current_version_options={"removal_policy": RemovalPolicy.DESTROY},
            layers=[layer],
            environment={
                "POWERTOOLS_SERVICE_NAME": "InfraSetupLambda",
                "POWERTOOLS_METRICS_NAMESPACE": "InfraSetupLambda-NameSpace",
                "POWERTOOLS_LOG_LEVEL": "INFO",
            },
        )

        provider_role = iam.Role(
            self,
            f"{self.props['stack_name_base']}-OSSProviderRole",
            assumed_by=ServicePrincipal("lambda.amazonaws.com"),
        )
        provider_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "aoss:APIAccessAll",
                    "aoss:List*",
                    "aoss:Get*",
                    "aoss:Create*",
                    "aoss:Update*",
                    "aoss:Delete*",
                ],
                resources=["*"],
            )
        )

        provider = cr.Provider(
            self,
            f"{self.props['stack_name_base']}-OSSProvider",
            on_event_handler=index_lambda,
            log_group=LogGroup(
                self, "OSSIndexCreationProviderLogs", retention=RetentionDays.ONE_DAY
            ),
            role=provider_role,
        )

        custom_resource = core.CustomResource(
            self,
            "OSSIndexCreationCustomResource",
            service_token=provider.service_token,
            properties={
                "collection_endpoint": self.collection.attr_collection_endpoint,
                "data_access_policy_name": self.dataAccessPolicy.name,
                "index_name": self.props["oss_index_name"],
                "embedding_model_id": self.props["embedding_model_id"],
            },
            removal_policy=RemovalPolicy.DESTROY,
        )
        custom_resource.node.add_dependency(provider)


# Backward compatibility alias
ReVIEWOSSConstruct = OSSVectorStoreConstruct
