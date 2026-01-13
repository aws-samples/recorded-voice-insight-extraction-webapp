# CloudWatch Logs Setup for API Gateway

## Problem

When deploying the CDK stack, you may encounter this error:

```
CREATE_FAILED | AWS::ApiGatewayV2::Stage | review-app-api/web_socket_api_stage
Resource handler returned message: "CloudWatch Logs role ARN must be set in account 
settings to enable logging (Service: AmazonApiGatewayV2; Status Code: 400; 
Error Code: BadRequestException)"
```

This occurs because API Gateway requires an account-level IAM role to write logs to CloudWatch. This is a one-time setup per AWS account/region.

## Solution

Run the setup script from the repository root:

```bash
./scripts/cloudwatch-role.sh
```

Or with a specific region:

```bash
./scripts/cloudwatch-role.sh us-west-2
```

After the script completes, retry your CDK deployment:

```bash
cd infra
cdk deploy --all
```

## What the Script Does

1. Creates an IAM role `APIGatewayCloudWatchLogsRole` that API Gateway can assume
2. Attaches the AWS managed policy `AmazonAPIGatewayPushToCloudWatchLogs`
3. Configures API Gateway account settings to use this role

## Manual Setup

If you prefer to set this up manually or via the console:

1. Go to IAM → Roles → Create Role
2. Select "API Gateway" as the trusted entity
3. Attach policy: `AmazonAPIGatewayPushToCloudWatchLogs`
4. Name it: `APIGatewayCloudWatchLogsRole`
5. Go to API Gateway → Settings → CloudWatch log role ARN
6. Enter: `arn:aws:iam::<ACCOUNT_ID>:role/APIGatewayCloudWatchLogsRole`
