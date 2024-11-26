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

from aws_cdk import NestedStack
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_lambda as _lambda
from infra.constructs.kb_constructs import (
    ReVIEWKnowledgeBaseConstruct,
    ReVIEWKnowledgeBaseRole,
    ReVIEWKnowledgeBaseSyncConstruct,
)
from infra.constructs.oss_constructs import ReVIEWOSSConstruct


class ReVIEWRAGStack(NestedStack):
    """Stack to deploy both knowledge base and opensearch serverless"""

    def __init__(
        self,
        scope,
        props: dict,
        ddb_lambda: _lambda.Function,
        source_bucket: s3.Bucket,
        **kwargs,
    ):
        """source_bucket is the s3 bucket from which KB will grab text files to index, already created in backend
        ddb_lambda is provided because KB sync step functions invoke a lambda to store
        job status in a dynamo table"""
        self.props = props
        construct_id = props["stack_name_base"] + "-rag"
        description = "ReVIEW Application - RAG stack (v1.0.0)"
        super().__init__(scope, construct_id, description=description, **kwargs)

        # Setup KB role
        # It is given the source bucket because KB has to have access to that bucket
        self.kb_role_construct = ReVIEWKnowledgeBaseRole(
            self, props=props, source_bucket=source_bucket
        )

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
            source_bucket=source_bucket,
        )

        # Don't deploy kb until oss is ready (including launching
        # lambda functions to create indices)
        self.kb_construct.node.add_dependency(self.oss_construct)

        # Construct to handle syncing of knowledge base
        self.kb_sync_construct = ReVIEWKnowledgeBaseSyncConstruct(
            self,
            props=props,
            knowledge_base=self.kb_construct.knowledge_base,
            data_source=self.kb_construct.data_source,
            ddb_lambda=ddb_lambda,
            source_bucket=source_bucket,
        )
