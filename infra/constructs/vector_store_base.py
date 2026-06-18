# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from abc import abstractmethod
from constructs import Construct
import aws_cdk.aws_iam as iam


class VectorStoreConstruct(Construct):
    """Base class for vector store implementations"""

    @property
    @abstractmethod
    def vector_store_arn(self) -> str:
        """Return ARN of the vector store resource"""
        raise NotImplementedError

    @property
    @abstractmethod
    def vector_store_type(self) -> str:
        """Return type identifier for KB configuration"""
        raise NotImplementedError


def create_vector_store(
    scope: Construct,
    props: dict,
    kb_role: iam.Role,
) -> VectorStoreConstruct:
    """Factory function to create appropriate vector store based on config."""
    vector_store_type = props["vector_store_type"]

    if vector_store_type == "OPENSEARCH_SERVERLESS":
        from constructs.oss_constructs import OSSVectorStoreConstruct

        return OSSVectorStoreConstruct(scope, props, kb_role)
    elif vector_store_type == "S3":
        from constructs.s3_vector_store_constructs import S3VectorStoreConstruct

        return S3VectorStoreConstruct(scope, props, kb_role)
    else:
        raise ValueError(f"Unsupported vector_store_type: {vector_store_type}")
