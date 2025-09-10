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

from aws_cdk import Stack, CfnOutput
from constructs import Construct
from .backend_stack import ReVIEWBackendStack
from .rag_stack import ReVIEWRAGStack
from .api_stack import ReVIEWAPIStack
from .frontend_stack import ReVIEWFrontendStack


"""
ReVIEW Parent Stack Definition
"""


class ReVIEWStack(Stack):
    """Primary parent ReVIEW Application stack, main purpose is to deploy
    the child NestedStacks from one place"""

    def __init__(self, scope: Construct, props: dict, **kwargs) -> None:
        construct_id = props["stack_name_base"]
        description = (
            "ReVIEW Application - Parent stack (v1.3.2) - a2F6dQ== (uksb-bpfhuojorc)"
        )

        super().__init__(scope, construct_id, description=description, **kwargs)

        # Backend stack, setting up buckets and lambda functions
        # to preprocess and transcribe uploaded files, etc
        self.backend_stack = ReVIEWBackendStack(self, props=props)

        # RAG stack (OSS + Bedrock KB)
        # DynamoDB handler lambda provided because the knowledge base ingest/sync
        # functions use it to update job statuses in a dynamoDB table
        # Source_bucket was created in the backend_stack, it's where the
        # RAG stack grabs transcripts and ingests them into a knowledge base
        self.rag_stack = ReVIEWRAGStack(
            self,
            props=props,
            ddb_lambda=self.backend_stack.ddb_handler_lambda,
            source_bucket=self.backend_stack.bucket,
        )

        # API stack for frontend to communicate with backend
        self.api_stack = ReVIEWAPIStack(
            self,
            props=props,
            llm_lambda=self.backend_stack.llm_lambda,
            ddb_lambda=self.backend_stack.ddb_handler_lambda,
            knowledge_base=self.rag_stack.kb_construct.knowledge_base,
            presigned_url_lambda=self.backend_stack.presigned_url_lambda,
            kb_job_deletion_lambda=self.rag_stack.kb_sync_construct.deletion_lambda,
            subtitle_lambda=self.backend_stack.subtitle_lambda,
            analysis_templates_lambda=self.backend_stack.analysis_templates_lambda,
            source_bucket=self.backend_stack.bucket,
        )

        # Frontend stack (React application in S3 behind CloudFront)
        # Use SSM parameters instead of direct resource references to avoid dependency issues
        self.frontend_stack = ReVIEWFrontendStack(
            self,
            props=props,
        )

        # Add explicit dependencies to ensure frontend is deployed after backend stacks
        # This ensures SSM parameters are created before frontend tries to read them
        self.frontend_stack.add_dependency(self.backend_stack)
        self.frontend_stack.add_dependency(self.rag_stack)
        self.frontend_stack.add_dependency(self.api_stack)

        # Save cfn distribution domain name as output, for convenience
        CfnOutput(
            self,
            "ReVIEW Frontend URL",
            value=self.frontend_stack.distribution.distribution_domain_name,
        )
        # Add source backend bucket to CFN output for users to easily find
        CfnOutput(
            self,
            "ReVIEW Media Source Bucket",
            value=self.backend_stack.bucket.bucket_name,
        )
