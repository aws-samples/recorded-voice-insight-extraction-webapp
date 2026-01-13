#!/bin/bash
# Setup CloudWatch Logs role for API Gateway
# This is a one-time setup per AWS account/region
# Usage: ./scripts/cloudwatch-role.sh [region]

set -e

REGION="${1:-us-east-1}"
ROLE_NAME="APIGatewayCloudWatchLogsRole"

echo "Setting up API Gateway CloudWatch Logs role in region: $REGION"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

# Create the IAM role (skip if exists)
if aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null; then
    echo "Role $ROLE_NAME already exists"
else
    echo "Creating IAM role: $ROLE_NAME"
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "apigateway.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }'

    # Attach the managed policy for CloudWatch Logs
    echo "Attaching CloudWatch Logs policy"
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs

    # Wait for role to propagate
    echo "Waiting for role to propagate..."
    sleep 10
fi

# Configure API Gateway to use this role
echo "Updating API Gateway account settings"
aws apigateway update-account \
    --region "$REGION" \
    --patch-operations op=replace,path=/cloudwatchRoleArn,value="$ROLE_ARN"

echo "Done! API Gateway can now write to CloudWatch Logs."
echo "Role ARN: $ROLE_ARN"
