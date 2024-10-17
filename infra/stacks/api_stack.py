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

from aws_cdk import Stack

from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import RemovalPolicy
from aws_cdk import aws_apigateway as apigw

from aws_cdk import CfnOutput


class ReVIEWAPIStack(Stack):
    """Construct for API Gateway separating frontend and backend
    REST endpoints associated with lambdas are provided for the frontend.
    Only the frontend_execution_role will have access to the API"""

    def __init__(
        self,
        scope,
        props: dict,
        llm_lambda: _lambda.Function,
        ddb_lambda: _lambda.Function,
        kb_query_lambda: _lambda.Function,
        **kwargs,
    ):
        self.props = props
        construct_id = props["stack_name_base"] + "-api"
        super().__init__(scope, construct_id, **kwargs)

        self.create_gateway()
        self.associate_lambda_with_gateway(llm_lambda, "llm")
        self.associate_lambda_with_gateway(ddb_lambda, "ddb")
        self.associate_lambda_with_gateway(kb_query_lambda, "kb")

        # Output the API URL and API Key
        CfnOutput(self, "ApiUrl", value=self.api.url)

    def create_gateway(self):
        # Create API Gateway which allows access from within this same AWS account

        # TODO: get some form of auth working...

        # this_account_id = Stack.of(self).account
        # same_account_policy_document = iam.PolicyDocument(
        #     statements=[
        #         iam.PolicyStatement(
        #             effect=iam.Effect.ALLOW,
        #             actions=["execute-api:Invoke"],
        #             principals=[iam.AnyPrincipal()],
        #             resources=["execute-api:/*"],
        #             # https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html
        #             conditions={"StringEquals": {"aws:SourceAccount": this_account_id}},
        #         )
        #     ]
        # )
        self.api = apigw.RestApi(
            self,
            f"{self.props['unique_stack_name']}-api",
            rest_api_name=f"{self.props['unique_stack_name']}-api",
            description="API for ReVIEW application",
            # default_method_options=apigw.MethodOptions(
            #     authorization_type=apigw.AuthorizationType.IAM
            # ),
            # policy=same_account_policy_document,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,  # TODO: limit to frontend
                allow_methods=apigw.Cors.ALL_METHODS,  # TODO: limit to frontend
            ),
        )

        # Enable IAM authentication for the API
        self.api.root.add_method("ANY", authorization_type=apigw.AuthorizationType.IAM)

        self.api.apply_removal_policy(RemovalPolicy.DESTROY)

    def associate_lambda_with_gateway(
        self, my_lambda: _lambda.Function, resource_name: str
    ):
        # Create a resource for the Lambda function
        resource = self.api.root.add_resource(resource_name)

        # Integrate Lambda function with API Gateway
        integration = apigw.LambdaIntegration(my_lambda)

        # Add POST method to resource
        resource.add_method("POST", integration)

    def grant_API_access(self, backend_api: apigw.RestApi):
        """Modify the backend API policies to allow access from the frontend IAM role"""

        # Create an IAM policy to allow frontend access to the API,
        # and block all other access to the API
        allow_frontend_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["execute-api:Invoke"],
            resources=[backend_api.arn_for_execute_api()],
            principals=[iam.ArnPrincipal(self.app_execution_role.role_arn)],
        )
        deny_policy = iam.PolicyStatement(
            effect=iam.Effect.DENY,
            principals=[iam.AnyPrincipal()],
            actions=["execute-api:Invoke"],
            resources=[backend_api.arn_for_execute_api()],
            conditions={
                "StringNotEquals": {
                    "aws:PrincipalArn": self.app_execution_role.role_arn
                }
            },
        )

        # Create a resource policy for the API
        resource_policy = iam.PolicyDocument(
            statements=[allow_frontend_policy, deny_policy]
        )

        # Apply the resource policy to the API
        backend_api.policy = resource_policy
        # TODO:
        """
        Remember to update your frontend application code to sign the API requests with AWS Signature Version 4 using the IAM credentials. This is typically done using the AWS SDK for the language your frontend is written in.

        Maybe adjust the CORS settings to be more restrictive, specifying only the origins that your frontend application will be served from, instead of allowing all origins.
        """
