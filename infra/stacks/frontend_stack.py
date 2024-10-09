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

from aws_cdk import aws_cognito as cognito

import boto3
from aws_cdk import Duration, RemovalPolicy, CfnOutput, Stack
from aws_cdk import aws_ec2 as ec2

import os
from pathlib import Path
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as cfo

from aws_cdk import aws_ecs_patterns as ecs_patterns
import cdk_nag


class ReVIEWFrontendStack(Stack):
    def __init__(self, scope, props: dict, **kwargs):
        self.props = props
        construct_id = props["stack_name_base"] + "-frontend"
        super().__init__(scope, construct_id, **kwargs)

        # Note: all props are exported as env variables in the streamlit
        # docker container (e.g. backend bucket names, table names, etc)

        # if app.py calls ReVIEWStack(app,"ReVIEW-prod") then
        # construct_id here is "review-prod-streamlit"
        self.fe_stack_name = construct_id

        self.setup_cognito()
        self.create_frontend_app_execution_role()
        self.deploy_fargate_service()
        self.custom_header_name = f"{self.fe_stack_name}-custom-header"
        self.custom_header_value = f"{self.fe_stack_name}-StreamlitCfnHeaderVal"
        self.set_listener_custom_headers()
        self.create_cloudfront_distribution()

        # Save cfn distribution domain name as output, for convenience
        CfnOutput(
            self,
            f"{self.fe_stack_name}-FrontendUrl",
            value=self.cfn_distribution.domain_name,
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.app_execution_role,
            suppressions=[
                {"id": "AwsSolutions-IAM4", "reason": "Managed policies ok"},
                {"id": "AwsSolutions-IAM5", "reason": "Wildcard ok"},
            ],
        )

    def deploy_fargate_service(self):
        """Deploy VPC, cluster, app image into fargate"""
        # Create a VPC
        self.vpc = ec2.Vpc(
            self,
            f"{self.fe_stack_name}-WebappVpc",
            max_azs=2,
        )
        # Create an ECS cluster in the VPC
        self.cluster = ecs.Cluster(
            self, f"{self.fe_stack_name}-WebappCluster", vpc=self.vpc
        )
        # Docker build the frontend UI image
        self.app_image = ecs.ContainerImage.from_asset(
            os.path.join(Path(__file__).parent.parent.parent, "frontend"),
            # platform = Platform.LINUX_AMD64 ## Use this if Docker building on a mac OS
        )
        # Deploy the frontend UI image into a load balanced fargate service in the cluster
        self.service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            f"{self.fe_stack_name}-AppService",
            cluster=self.cluster,
            cpu=1024,
            desired_count=1,  # Possibly increase this to handle more concurrent requests
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=self.app_image,
                container_port=8501,
                task_role=self.app_execution_role,
                environment={
                    "COGNITO_CLIENT_ID": self.cognito_user_pool_client.user_pool_client_id,
                    "COGNITO_POOL_ID": self.cognito_user_pool_id,
                    **self.props,
                },
            ),
            # Memory needs to be large enough to handle large media uploads
            # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_ecs_patterns.ApplicationLoadBalancedFargateService.html#memorylimitmib
            memory_limit_mib=8192,
            public_load_balancer=True,
            # Max length is 32 characters for ALB names
            load_balancer_name=f"{self.fe_stack_name}-alb"[-32:],
        )

    def set_listener_custom_headers(self):
        # To increase security, fargate service only responds when http requests
        # include this specific header name and value.
        # This prevents people from connecting to the open-to-the-internet
        # load balancer directly.
        # Ultimately, the cloudfront distribution will construct requests
        # with this header.

        self.service.listener.add_action(
            "forward-custom-header",
            priority=1,
            conditions=[
                elbv2.ListenerCondition.http_header(
                    self.custom_header_name, [self.custom_header_value]
                )
            ],
            action=elbv2.ListenerAction.forward([self.service.target_group]),
        )

        self.service.listener.add_action(
            "new-default-action", action=elbv2.ListenerAction.fixed_response(403)
        )

    def create_frontend_app_execution_role(self):
        self.app_execution_role = iam.Role(
            self,
            f"{self.fe_stack_name}-frontendAppExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        # TODO: is this necessary?
        self.app_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonAPIGatewayInvokeFullAccess"
            )
        )
        # Frontend UI needs read/write access to s3
        self.app_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
        )
        # Frontend UI needs read/write access dynamodb
        self.app_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess")
        )
        # Frontend UI needs to access cognito to check logins
        self.app_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonCognitoReadOnly")
        )
        # Frontend UI needs to call bedrock
        self.app_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
        )

    def setup_cognito(self):
        # Cognito User Pool
        user_pool_common_config = {
            "id": "review-app-cognito-user-pool-id",
            "user_pool_name": self.props["cognito_pool_name"],
            "auto_verify": cognito.AutoVerifiedAttrs(email=True),
            "removal_policy": RemovalPolicy.RETAIN,
            "password_policy": cognito.PasswordPolicy(
                min_length=8,
                require_digits=False,
                require_lowercase=False,
                require_uppercase=False,
                require_symbols=False,
            ),
            "account_recovery": cognito.AccountRecovery.EMAIL_ONLY,
            "advanced_security_mode": cognito.AdvancedSecurityMode.ENFORCED,
            "deletion_protection": True,
        }

        # Check if a user pool with this name already exists
        # Unfortunately there is no way to do this w/ constructs
        # (only search by ID, which I don't have a priori)
        cognito_client = boto3.client("cognito-idp", "us-east-1")
        existing_pools = cognito_client.list_user_pools(MaxResults=10)["UserPools"]
        found_existing_pool = False
        for pool in existing_pools:
            if pool["Name"] == self.props["cognito_pool_name"]:
                self.cognito_user_pool = cognito.UserPool.from_user_pool_id(
                    self, "review-app-cognito-user-pool", user_pool_id=pool["Id"]
                )
                found_existing_pool = True
                break
        if not found_existing_pool:
            # Create a new user pool
            self.cognito_user_pool = cognito.UserPool(self, **user_pool_common_config)

        self.cognito_user_pool_id = self.cognito_user_pool.user_pool_id

        self.cognito_user_pool_client = self.cognito_user_pool.add_client(
            "review-app-cognito-client",
            user_pool_client_name="review-app-cognito-client",
            generate_secret=False,
            access_token_validity=Duration.minutes(30),
            auth_flows=cognito.AuthFlow(user_srp=True),
        )

        self.cognito_client_id = self.cognito_user_pool_client.user_pool_client_id

    def create_cloudfront_distribution(self):
        self.cfn_distribution = cloudfront.Distribution(
            self,
            f"{self.fe_stack_name}-cloudfront-id",
            default_behavior=cloudfront.BehaviorOptions(
                origin=cfo.LoadBalancerV2Origin(
                    self.service.load_balancer,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                    http_port=80,
                    origin_path="/",
                    custom_headers={self.custom_header_name: self.custom_header_value},
                ),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_AND_CLOUDFRONT_2022,
                response_headers_policy=cloudfront.ResponseHeadersPolicy.CORS_ALLOW_ALL_ORIGINS,
                compress=False,
            ),
        )
