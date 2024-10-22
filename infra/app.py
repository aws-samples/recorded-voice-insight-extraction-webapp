#!/usr/bin/env python3
import sys
import os

# Add repo top dir to system path to facilitate absolute imports elsewhere
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aws_cdk as cdk

from stacks.backend_stack import ReVIEWBackendStack
from stacks.frontend_stack import ReVIEWFrontendStack
from stacks.rag_stack import ReVIEWRAGStack
from stacks.api_stack import ReVIEWAPIStack
from utils.config_manager import ConfigManager

config_manager = ConfigManager("config.yaml")
# Initial props consist of configuration parameters
# More props are added between stack deployments to pass inter-stack variables
props = config_manager.get_props()

app = cdk.App()

# Backend stack
backend_stack = ReVIEWBackendStack(
    app,
    props,
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.
    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.
    # env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */
    # env=cdk.Environment(account='123456789012', region='us-east-1'),
    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
)

# RAG stack (OSS + Bedrock KB)
# DynamoDB handler lambda provided because the knowledge base ingest/sync
# functions use it to update job statuses in a dynamoDB table
rag_stack = ReVIEWRAGStack(app, props, ddb_lambda=backend_stack.ddb_handler_lambda)

# API stack for frontend to communicate with backend
api_stack = ReVIEWAPIStack(
    app,
    props,
    llm_lambda=backend_stack.llm_lambda,
    ddb_lambda=backend_stack.ddb_handler_lambda,
    kb_query_lambda=rag_stack.kb_construct.query_lambda,
    presigned_url_lambda=backend_stack.presigned_url_lambda,
)

# Frontend stack
frontend_stack = ReVIEWFrontendStack(
    app,
    props,
    backend_api_url=api_stack.api.url,
    cognito_pool=api_stack.cognito_user_pool,
)


# Enforce ordering of stacks via dependency
rag_stack.add_dependency(backend_stack)
frontend_stack.add_dependency(rag_stack)
frontend_stack.add_dependency(api_stack)

app.synth()
