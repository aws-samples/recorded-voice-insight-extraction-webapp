#!/usr/bin/env python3

import aws_cdk as cdk
from stacks.review_stack import ReVIEWStack

app = cdk.App()
ReVIEWStack(
    app,
    # This ID is used to name s3 buckets, databases, etc.
    # You can deploy two fully independent stacks into the same account if you use different IDs
    # Stack names can only be alphanumeric and hyphens
    # Stack names should be very short (max 14 characters)
    # Stack names should be unique, as s3 buckets named after it must be globally unique.
    # Note: the cognito user-pool name is hard coded and shared by all stacks for now.
    "ReVIEW-dev-339712833620",
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

app.synth()
