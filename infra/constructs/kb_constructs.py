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

    def __init__(self, scope, construct_id, props: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        self.props = props

        # Setup KB role
        self.setup_kb_role()

    def setup_kb_role(self):
        # Create KB Role
        self.kbrole = iam.Role(
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

        # create an SSM parameters which store export values
        # ssm.StringParameter(
        #     self,
        #     f"kbRoleArn-{self.kb_role_name}",
        #     parameter_name=f"kbRoleArn-{self.kb_role_name}",
        #     string_value=self.kbrole.role_arn,
        # )
        # print(
        #     f"Created kbRoleArn param with name kbRoleArn-{self.kb_role_name} and value {self.kbrole.role_arn}"
        # )
