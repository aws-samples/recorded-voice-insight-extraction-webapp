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

import boto3
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cognito as cognito
from aws_cdk import (
    aws_lambda as _lambda,
)


class ReVIEWAPIStack(Stack):
    """Construct for API Gateway separating frontend and backend.
    REST endpoints associated with backend lambdas are provided for the frontend.
    Cognito is used for API auth."""

    def __init__(
        self,
        scope,
        props: dict,
        llm_lambda: _lambda.Function,
        ddb_lambda: _lambda.Function,
        kb_query_lambda: _lambda.Function,
        presigned_url_lambda: _lambda.Function,
        **kwargs,
    ):
        self.props = props
        construct_id = props["stack_name_base"] + "-api"
        description = "ReVIEW (uksb-7ai2e5cqbn) (tag: API)"
        super().__init__(scope, construct_id, description=description, **kwargs)

        self.setup_cognito_pool()
        self.create_gateway()
        self.associate_lambda_with_gateway(llm_lambda, "llm")
        self.associate_lambda_with_gateway(ddb_lambda, "ddb")
        self.associate_lambda_with_gateway(kb_query_lambda, "kb")
        self.associate_lambda_with_gateway(presigned_url_lambda, "s3-presigned")

        # Output the API URL and API Key
        CfnOutput(self, "ApiUrl", value=self.api.url)

    def setup_cognito_pool(self):
        # Cognito User Pool (stored as self.cognito_user_pool)
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

        # Check if a user pool with this name already exists, else create one
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

    def create_gateway(self):
        # Create API Gateway and Cognito authorizer

        self.api = apigw.RestApi(
            self,
            f"{self.props['unique_stack_name']}-api",
            rest_api_name=f"{self.props['unique_stack_name']}-api",
            description="API for ReVIEW application",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,  # All origins allowed
                allow_methods=apigw.Cors.ALL_METHODS,  # All methods have an authorizer
            ),
            deploy=True,
        )

        self.api.apply_removal_policy(RemovalPolicy.DESTROY)

        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "ReVIEWAPIAuthorizer",
            cognito_user_pools=[self.cognito_user_pool],
            identity_source=apigw.IdentitySource.header(
                "Authorization"
            ),  # This is the header expression which includes the bearer token
            results_cache_ttl=Duration.seconds(0),  # Disable caching
        )

    def associate_lambda_with_gateway(
        self, my_lambda: _lambda.Function, resource_name: str
    ):
        # Create a resource for the Lambda function
        resource = self.api.root.add_resource(resource_name)

        # Integrate Lambda function with API Gateway
        integration = apigw.LambdaIntegration(my_lambda)

        # Add POST method to resource, with Cognito authorizer
        resource.add_method(
            "POST",
            integration,
            authorizer=self.authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )
