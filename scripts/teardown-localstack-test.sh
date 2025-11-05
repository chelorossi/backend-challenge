#!/bin/bash
# Destroy CDK infrastructure from LocalStack

set -e

echo "🗑️  Destroying CDK infrastructure from LocalStack..."

# Check if LocalStack is running
if ! curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then
    echo "⚠️  LocalStack is not running. Nothing to destroy."
    exit 0
fi

# Set LocalStack environment variables
export AWS_ENDPOINT_URL=http://localhost:4566
export CDK_DEFAULT_ACCOUNT=000000000000
export CDK_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=us-east-1

# Change to infrastructure directory
cd "$(dirname "$0")/../infrastructure"

# Destroy stacks using AWS CLI (since CDK destroy may have issues with LocalStack)
echo "🏗️  Destroying stacks..."
aws cloudformation delete-stack \
    --stack-name TaskManagementProcessing-test \
    --endpoint-url http://localhost:4566 \
    --region us-east-1 \
    2>/dev/null || true

aws cloudformation delete-stack \
    --stack-name TaskManagementApi-test \
    --endpoint-url http://localhost:4566 \
    --region us-east-1 \
    2>/dev/null || true

aws cloudformation delete-stack \
    --stack-name TaskManagementShared-test \
    --endpoint-url http://localhost:4566 \
    --region us-east-1 \
    2>/dev/null || true

# Wait for stacks to be deleted
echo "⏳ Waiting for stacks to be deleted..."
sleep 3

# Remove outputs file
cd "$(dirname "$0")/.."
rm -f tests/localstack-outputs.json

echo "✅ Infrastructure destroyed successfully!"
