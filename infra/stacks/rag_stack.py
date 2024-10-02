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
from infra.constructs.kb_constructs import (
    ReVIEWKnowledgeBaseRole,
    ReVIEWKnowledgeBaseConstruct,
)
from infra.constructs.oss_constructs import ReVIEWOSSConstruct


class ReVIEWRAGStack(Stack):
    """Stack to deploy both knowledge base and opensearch serverless"""

    def __init__(self, scope, props: dict, **kwargs):
        self.props = props
        construct_id = props["stack_name_base"] + "-rag"
        super().__init__(scope, construct_id, **kwargs)

        # Setup KB role, which will be available with name props.kb_role_name
        self.kb_role_construct = ReVIEWKnowledgeBaseRole(self, props=props)

        # Deploy OSS collection, with data access allowed to kb_role
        self.oss_construct = ReVIEWOSSConstruct(
            self,
            props=props,
            data_access_principal_roles=[self.kb_role_construct.kb_role],
        )

        # Deploy KB on top of OSS collection, providing KB role and collection arn
        self.kb_construct = ReVIEWKnowledgeBaseConstruct(
            self,
            props=props,
            kb_principal_role=self.kb_role_construct.kb_role,
            oss_collection_arn=self.oss_construct.collection.attr_arn,
        )

        # Don't deploy kb until oss is ready (including launching
        # lambda functions to create indices? Not sure if that works)
        self.kb_construct.node.add_dependency(self.oss_construct)
