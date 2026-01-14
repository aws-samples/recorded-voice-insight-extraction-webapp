# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import CfnResource, RemovalPolicy, CfnOutput
import aws_cdk.aws_iam as iam
from constructs.vector_store_base import VectorStoreConstruct

# Embedding model dimensions
EMBEDDING_DIMENSIONS = {
    "amazon.titan-embed-text-v1": 1536,
    "amazon.titan-embed-text-v2:0": 1024,
    "cohere.embed-english-v3": 1024,
    "cohere.embed-multilingual-v3": 1024,
}


class S3VectorStoreConstruct(VectorStoreConstruct):
    """S3 Vector Bucket implementation for Bedrock Knowledge Base.
    
    Creates an S3 Vector Bucket and Index using the S3 Vectors service.
    """

    def __init__(
        self,
        scope: Construct,
        props: dict,
        kb_role: iam.Role,
        **kwargs,
    ):
        construct_id = props["stack_name_base"] + "-s3-vector-store"
        super().__init__(scope, construct_id, **kwargs)

        self.props = props
        bucket_suffix = props["s3_vector_bucket_suffix"]
        self.bucket_name = f"{props['stack_name_base']}-{bucket_suffix}"
        self.index_name = f"{props['stack_name_base']}-idx"

        # Get embedding dimension from model ID
        embedding_model_id = props["embedding_model_id"]
        self.dimension = EMBEDDING_DIMENSIONS.get(embedding_model_id, 1024)

        # Create S3 Vector Bucket using CfnResource (L1)
        self.vector_bucket = CfnResource(
            self,
            "VectorBucket",
            type="AWS::S3Vectors::VectorBucket",
            properties={
                "VectorBucketName": self.bucket_name,
            },
        )
        self.vector_bucket.apply_removal_policy(RemovalPolicy.DESTROY)

        # Create Vector Index
        self.vector_index = CfnResource(
            self,
            "VectorIndex",
            type="AWS::S3Vectors::Index",
            properties={
                "VectorBucketName": self.bucket_name,
                "IndexName": self.index_name,
                "DataType": "float32",
                "Dimension": self.dimension,
                "DistanceMetric": "cosine",
            },
        )
        self.vector_index.node.add_dependency(self.vector_bucket)
        self.vector_index.apply_removal_policy(RemovalPolicy.DESTROY)

        CfnOutput(
            self,
            "VectorBucketName",
            value=self.bucket_name,
            description="S3 Vector Bucket name",
        )
        CfnOutput(
            self,
            "VectorIndexName",
            value=self.index_name,
            description="S3 Vector Index name",
        )

    @property
    def vector_store_arn(self) -> str:
        """Return the vector bucket ARN"""
        return self.vector_bucket.get_att("VectorBucketArn").to_string()

    @property
    def vector_index_arn(self) -> str:
        """Return the vector index ARN"""
        return self.vector_index.get_att("IndexArn").to_string()

    @property
    def vector_store_type(self) -> str:
        return "S3"
