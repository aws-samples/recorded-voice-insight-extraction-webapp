# Vector Store Options

ReVIEW supports two vector store backends for the Bedrock Knowledge Base:

| Option | Type Value | Use Case |
|--------|------------|----------|
| OpenSearch Serverless | `OPENSEARCH_SERVERLESS` | Custom search queries, high query volume |
| S3 Vectors | `S3` | Standard RAG, minimal operational overhead |

## Configuration

Set the vector store type in `infra/config.yaml`:

```yaml
vector_store:
  type: "S3"  # or "OPENSEARCH_SERVERLESS"

# Only used when type is "S3"
s3_vector_bucket:
  bucket_name_suffix: "vector-store"
```

Then deploy:

```bash
cd infra
cdk deploy --all
```

## Switching Vector Stores

> **Warning**: Switching vector stores requires re-ingesting all transcripts. Vectors cannot be migrated between backends.

1. Destroy the existing stack:
   ```bash
   cdk destroy --all --force
   ```

2. Update `config.yaml` with the new `vector_store.type` value

3. Redeploy:
   ```bash
   cdk deploy --all
   ```

4. Re-upload media files through the frontend

## Comparison

| Aspect | OpenSearch Serverless | S3 Vectors |
|--------|----------------------|------------|
| Deployment Time | 15-20 minutes | 5-10 minutes |
| Operational Overhead | Medium | Low |
| Query Flexibility | High (custom queries) | Standard (KB API only) |

---

# Developer Reference

This section describes the implementation for developers working on the codebase.

## Architecture

The vector store implementation uses a factory pattern to instantiate the appropriate backend based on configuration.

```
config.yaml
    │
    ▼
ConfigManager.get_props()
    │
    ▼
ReVIEWRAGStack
    │
    ▼
create_vector_store() ─────► OSSVectorStoreConstruct
    │                              or
    └──────────────────────► S3VectorStoreConstruct
                                   │
                                   ▼
                          ReVIEWKnowledgeBaseConstruct
```

## Key Files

| File | Purpose |
|------|---------|
| `infra/constructs/vector_store_base.py` | Base class and factory function |
| `infra/constructs/oss_constructs.py` | OpenSearch Serverless implementation |
| `infra/constructs/s3_vector_store_constructs.py` | S3 Vectors implementation |
| `infra/constructs/kb_constructs.py` | Knowledge Base construct (consumes vector store ARN) |
| `infra/stacks/rag_stack.py` | Orchestrates vector store and KB creation |
| `infra/utils/config_manager.py` | Parses `vector_store_type` from config |

## Factory Pattern

The factory function in `vector_store_base.py` returns the appropriate construct:

```python
def create_vector_store(scope, props, kb_role) -> VectorStoreConstruct:
    if props["vector_store_type"] == "OPENSEARCH_SERVERLESS":
        return OSSVectorStoreConstruct(scope, props, kb_role)
    elif props["vector_store_type"] == "S3":
        return S3VectorStoreConstruct(scope, props, kb_role)
```

Both implementations expose:
- `vector_store_arn` - ARN passed to Knowledge Base
- `vector_store_type` - Type identifier for storage configuration

## RAG Stack Usage

The RAG stack uses the factory without conditional logic:

```python
# Create vector store via factory
self.vector_store = create_vector_store(self, props, kb_role)

# Get index ARN for S3 vector stores
vector_index_arn = None
if props["vector_store_type"] == "S3":
    vector_index_arn = self.vector_store.vector_index_arn

# Pass ARNs to Knowledge Base
self.kb_construct = ReVIEWKnowledgeBaseConstruct(
    ...,
    vector_store_arn=self.vector_store.vector_store_arn,
    vector_index_arn=vector_index_arn,
)
```

## S3 Vectors Implementation

S3 Vectors is a specialized AWS service for vector storage (not regular S3). The implementation creates:

1. **AWS::S3Vectors::VectorBucket** - Container for vector data
2. **AWS::S3Vectors::Index** - Vector index with dimension and distance metric

```python
# Vector bucket
self.vector_bucket = CfnResource(
    self, "VectorBucket",
    type="AWS::S3Vectors::VectorBucket",
    properties={"VectorBucketName": bucket_name},
)

# Vector index with embedding dimension
self.vector_index = CfnResource(
    self, "VectorIndex",
    type="AWS::S3Vectors::Index",
    properties={
        "VectorBucketName": bucket_name,
        "IndexName": index_name,
        "DataType": "float32",
        "Dimension": 1024,  # Matches embedding model
        "DistanceMetric": "cosine",
    },
)
```

## Knowledge Base Storage Configuration

The `ReVIEWKnowledgeBaseConstruct` builds the appropriate storage configuration based on `vector_store_type`:

**OpenSearch Serverless:**
```python
storage_config = StorageConfigurationProperty(
    type="OPENSEARCH_SERVERLESS",
    opensearch_serverless_configuration=...,
)
```

**S3 Vectors:**
```python
# Uses escape hatch since S3VectorsConfiguration isn't in CDK yet
cfn_kb.add_property_override(
    "StorageConfiguration.S3VectorsConfiguration",
    {
        "VectorBucketArn": vector_store_arn,
        "IndexArn": vector_index_arn,
    },
)
```

## IAM Permissions

The `ReVIEWKnowledgeBaseRole` conditionally adds AOSS permissions:

```python
if props["vector_store_type"] == "OPENSEARCH_SERVERLESS":
    inline_policies["OSSPolicy"] = ...  # aoss:APIAccessAll
```

S3 Vectors permissions are granted by the S3VectorStoreConstruct:
- `s3vectors:PutVectors`, `s3vectors:GetVectors`, `s3vectors:QueryVectors`, etc.

## Embedding Model Dimensions

The S3 Vectors index dimension must match the embedding model output:

```python
EMBEDDING_DIMENSIONS = {
    "amazon.titan-embed-text-v1": 1536,
    "amazon.titan-embed-text-v2:0": 1024,
    "cohere.embed-english-v3": 1024,
    "cohere.embed-multilingual-v3": 1024,
}
```

## Adding a New Vector Store Backend

1. Create `infra/constructs/<name>_constructs.py` inheriting from `VectorStoreConstruct`
2. Implement `vector_store_arn` and `vector_store_type` properties
3. Add the type to `create_vector_store()` factory
4. Add validation in `config_manager.py`
5. Add storage configuration handling in `kb_constructs.py`

## CDK Escape Hatch

The S3 Vectors storage configuration uses a CDK escape hatch because `S3VectorsConfiguration` is not yet available in the CDK L2 constructs (as of CDK 2.166.0). The escape hatch adds the property directly to the CloudFormation output:

```python
cfn_kb.add_property_override(
    "StorageConfiguration.S3VectorsConfiguration",
    {
        "VectorBucketArn": vector_store_arn,
        "IndexArn": vector_index_arn,
    },
)
```

When CDK adds native support, this can be replaced with the typed property.
