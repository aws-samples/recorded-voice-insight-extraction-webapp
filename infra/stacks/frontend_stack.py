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

import os
from pathlib import Path

import cdk_nag
from aws_cdk import CfnOutput, NestedStack, Duration, RemovalPolicy, Aws, BundlingOptions, DockerImage
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_iam as iam


class ReVIEWFrontendStack(NestedStack):
    def __init__(
        self,
        scope,
        props: dict,y
        **kwargs,
    ):
        self.props = props
        construct_id = props["stack_name_base"] + "-frontend"
        description = "ReVIEW Application - React Frontend stack"
        super().__init__(scope, construct_id, description=description, **kwargs)

        self.fe_stack_name = construct_id
        
        # Read configuration from SSM Parameter Store
        self.read_config_from_ssm()
        
        # Create S3 bucket for static website hosting
        self.create_website_bucket()
        
        # Create CloudFront distribution (static files only)
        self.create_cloudfront_distribution()
        
        # Deploy React application with configuration
        self.deploy_react_app()

        # Save CloudFront distribution domain name as output
        CfnOutput(
            self,
            f"{self.fe_stack_name}-FrontendUrl",
            value=f"https://{self.distribution.distribution_domain_name}",
        )

    def read_config_from_ssm(self):
        """Read frontend configuration from SSM Parameter Store."""
        # Read API Gateway URL
        self.api_gateway_url = ssm.StringParameter.value_for_string_parameter(
            self, f"/{self.props['stack_name_base']}/api-url"
        )

        # Read WebSocket API URL
        self.websocket_url = ssm.StringParameter.value_for_string_parameter(
            self, f"/{self.props['stack_name_base']}/websocket-url"
        )

        # Read Cognito User Pool ID
        self.cognito_user_pool_id = ssm.StringParameter.value_for_string_parameter(
            self, f"/{self.props['stack_name_base']}/cognito-pool-id"
        )

        # Read Cognito Client ID
        self.cognito_client_id = ssm.StringParameter.value_for_string_parameter(
            self, f"/{self.props['stack_name_base']}/cognito-client-id"
        )

    def create_website_bucket(self):
        """Create S3 bucket for static website hosting."""
        self.website_bucket = s3.Bucket(
            self,
            f"{self.fe_stack_name}-website-bucket",
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            auto_delete_objects=True,
            website_index_document="index.html",
            website_error_document="index.html",  # SPA routing support
        )

    def create_cloudfront_distribution(self):
        """Create CloudFront distribution for the React app (static files only)."""
        # Create Origin Access Control (OAC) for S3
        self.origin_access_control = cloudfront.S3OriginAccessControl(
            self, 
            f"{self.fe_stack_name}-s3-oac",
            description="OAC for ReVIEW React frontend"
        )

        # Create S3 origin for static files only
        s3_origin = origins.S3BucketOrigin.with_origin_access_control(
            self.website_bucket,
            origin_access_control=self.origin_access_control,
        )

        self.distribution = cloudfront.Distribution(
            self,
            f"{self.fe_stack_name}-distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=s3_origin,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                compress=True,
            ),
            # SPA routing support - redirect 404s to index.html
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),  # Don't cache error responses
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html", 
                    ttl=Duration.seconds(0),  # Handle S3 403s as SPA routes
                )
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            http_version=cloudfront.HttpVersion.HTTP2_AND_3,
        )

        # Grant CloudFront access to S3 bucket via bucket policy
        self.website_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontServicePrincipal",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[f"{self.website_bucket.bucket_arn}/*"],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{Aws.ACCOUNT_ID}:distribution/{self.distribution.distribution_id}"
                    }
                }
            )
        )

    def deploy_react_app(self):
        """Build and deploy the React application to S3."""
        app_path = os.path.join(Path(__file__).parent.parent.parent, "frontend")
        
        # Generate aws-exports.json configuration following the reference pattern
        exports_config = {
            "Auth": {
                "Cognito": {
                    "userPoolClientId": self.cognito_client_id,
                    "userPoolId": self.cognito_user_pool_id,
                }
            },
            "API": {
                "REST": {
                    "endpoint": self.api_gateway_url,  # Read from SSM
                }
            },
            "WebSocket": {
                "endpoint": self.websocket_url,  # Read from SSM
            },
        }

        # Create aws-exports.json as a deployment source
        exports_asset = s3deploy.Source.json_data("aws-exports.json", exports_config)

        # Create React app asset with Docker bundling
        react_asset = s3deploy.Source.asset(
            app_path,
            bundling=BundlingOptions(
                image=DockerImage.from_registry(
                    "public.ecr.aws/sam/build-nodejs18.x:latest"
                ),
                command=[
                    "sh",
                    "-c",
                    " && ".join([
                        "npm --cache /tmp/.npm install",
                        "npm --cache /tmp/.npm run build",
                        "cp -aur /asset-input/dist/* /asset-output/",
                    ]),
                ],
            ),
        )

        # Deploy both the React app and configuration
        self.deployment = s3deploy.BucketDeployment(
            self,
            f"{self.fe_stack_name}-deployment",
            sources=[react_asset, exports_asset],
            destination_bucket=self.website_bucket,
            distribution=self.distribution,
            prune=False,  # Don't delete files not in the deployment
        )
