#!/usr/bin/env python3
import sys
import os

# Add repo top dir to system path to facilitate absolute imports elsewhere
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aws_cdk as cdk

from stacks.review_stack import ReVIEWStack
from utils.config_manager import ConfigManager

config_manager = ConfigManager("config.yaml")

# Initial props consist of configuration parameters
# More props are added between stack deployments to pass inter-stack variables
props = config_manager.get_props()

app = cdk.App()

review_stack = ReVIEWStack(
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

app.synth()
