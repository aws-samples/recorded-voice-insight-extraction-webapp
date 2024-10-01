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
from constructs import Construct


class ReVIEWOSSConstruct(Construct):
    """Construct to create an OpenSearch serverless collection and index, with
    appropriate access policies etc.
    Provide the Bedrock KB principal role on instantiation of this construct
    to allow it access to the collection.
    """

    def __init__(
        self, scope, props: dict, data_access_principal_roles: list[iam.Role], **kwargs
    ):
        """data_access_principal_roles are the IAM roles which needs access to OSS collections,
        E.g. knowledge base, and any lambdas which create indices, etc"""
        self.props = props
        construct_id = f"{props['stack_name_base']}-oss"
        super().__init__(scope, construct_id, **kwargs)

        # Create a role for lambdas that will access this OSS
        #  (allowed resources are of form
        # "arn:aws:aoss:*:[ACCOUNT_ID]:collection/*")
        self.oss_lambda_role = self.create_oss_lambda_role()

        self.collection_name = props["oss_collection_name"]
        self.encryptionPolicy = self.create_encryption_policy()
        self.networkPolicy = self.create_network_policy()
        # Grant both input principal roles (e.g. bedrock KB) and
        # lambda role access to the data in the collection
        self.dataAccessPolicy = self.create_data_access_policy(
            data_access_principal_roles + [self.oss_lambda_role]
        )
        self.collection = self.create_collection()

        # Create all policies before creating the collection
        self.networkPolicy.node.add_dependency(self.encryptionPolicy)
        self.dataAccessPolicy.node.add_dependency(self.networkPolicy)
        self.collection.node.add_dependency(self.encryptionPolicy)

        # Create the OSS index (by creating a lambda to do so, and invoking it)
        self.create_oss_index()

    def create_encryption_policy(self) -> CfnSecurityPolicy:
        encryption_security_policy = json.dumps(
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

        return CfnSecurityPolicy(
            self,
            "EncryptionSecurityPolicy",
            policy=encryption_security_policy,
            name=f"{self.collection_name}-enc-pol",
            type="encryption",
        )

    def create_network_policy(self) -> CfnSecurityPolicy:
        network_security_policy = json.dumps(
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

        return CfnSecurityPolicy(
            self,
            "NetworkSecurityPolicy",
            policy=network_security_policy,
            name=f"{self.collection_name}-ntw-pol",
            type="network",
        )

    def create_collection(self) -> CfnCollection:
        return CfnCollection(
            self,
            "OpsSearchCollection",
            name=self.collection_name,
            description="Collection to be used for ReVIEW App search using OpenSearch Serverless",
            type="VECTORSEARCH",  # [SEARCH, TIMESERIES]
        )

    def create_data_access_policy(
        self, principal_roles: list[iam.Role]
    ) -> CfnAccessPolicy:
        """
        principal_roles are the principal which will need access to
        the collection (e.g. knowledge base role, lambda index creation role, etc)
        """

        data_access_policy = json.dumps(
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
                    "Principal": [
                        principal_role.role_arn for principal_role in principal_roles
                    ],
                    "Description": "ReVIEW Knowledge Base OSS data-access-rule",
                }
            ],
            indent=2,
        )

        return CfnAccessPolicy(
            self,
            "ReVIEWOSSDataAccessPolicy",
            name=f"{self.collection_name}",
            description="ReVIEW OSS data access policy",
            type="data",
            policy=data_access_policy,
        )

    def create_oss_lambda_role(self):
        """Role used by all lambdas interacting with this oss collection"""
        return iam.Role(
            self,
            f"{self.props['stack_name_base']}-OSSLambdaRole",
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
                            resources=[
                                f"arn:aws:aoss:*:{self.props['account_id']}:collection/*",
                                "arn:aws:logs:*:*:*",
                            ],
                        )
                    ]
                )
            },
        )

    def create_oss_index(self):
        """
        1. Create the lambda function that will create an index
        2. Invoke the lambda function to actually create the index (w/ custom resource stuff)
        """
        # dependency layer (includes requests, requests-aws4auth,opensearch-py, aws-lambda-powertools)
        dependency_layer = _lambda.LayerVersion(
            self,
            "dependency_layer",
            code=_lambda.Code.from_asset("lambdas/dependency_layer.zip"),
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_8,
                _lambda.Runtime.PYTHON_3_9,
                _lambda.Runtime.PYTHON_3_10,
            ],
            license="Apache-2.0",
            description="dependency_layer including requests, requests-aws4auth, aws-lambda-powertools, opensearch-py",
        )

        oss_index_creation_lambda = _lambda.Function(
            self,
            "ReVIEW-oss-index-creation-lambda",
            function_name=f"ReVIEW-{self.props['oss_index_name']}-InfraSetupLambda",
            code=Code.from_asset("lambdas/lambdas.zip"),
            handler="oss-create-index-lambda.lambda_handler",
            description="Lambda function to create OSS index for ReVIEW App",
            role=self.oss_lambda_role,
            memory_size=1024,
            timeout=Duration.minutes(14),
            runtime=Runtime.PYTHON_3_8,
            tracing=Tracing.ACTIVE,
            current_version_options={"removal_policy": RemovalPolicy.DESTROY},
            layers=[dependency_layer],
            environment={
                "POWERTOOLS_SERVICE_NAME": "InfraSetupLambda",
                "POWERTOOLS_METRICS_NAMESPACE": "InfraSetupLambda-NameSpace",
                "POWERTOOLS_LOG_LEVEL": "INFO",
            },
        )

        # Create custom resource provider, to trigger the index creation lambda
        oss_index_creation_provider = cr.Provider(
            self,
            f"{self.props['stack_name_base']}-OSSProvider",
            on_event_handler=oss_index_creation_lambda,
            log_group=LogGroup(
                self, "OSSIndexCreationProviderLogs", retention=RetentionDays.ONE_DAY
            ),
        )

        # Create a new custom resource consumer
        index_creation_custom_resource = core.CustomResource(
            self,
            "OSSIndexCreationCustomResource",
            service_token=oss_index_creation_provider.service_token,
            # These get passed to the lambda function in the event, as event['ResourceProperties']
            properties={
                "collection_endpoint": self.collection.attr_collection_endpoint,
                "data_access_policy_name": self.dataAccessPolicy.name,
                "index_name": self.props["oss_index_name"],
                "embedding_model_id": self.props["embedding_model_id"],
            },
        )

        # Ensure the consumer is created after the provider
        index_creation_custom_resource.node.add_dependency(oss_index_creation_provider)
