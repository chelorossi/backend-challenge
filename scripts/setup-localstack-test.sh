#!/bin/bash
# Deploy CDK infrastructure to LocalStack for testing

set -e

echo "🚀 Deploying CDK infrastructure to LocalStack..."

# Check if LocalStack is running
if ! curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then
    echo "❌ LocalStack is not running. Please start it with: docker-compose up -d"
    exit 1
fi

# Set LocalStack environment variables
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ENDPOINT_URL_S3=http://localhost:4566
export CDK_DEFAULT_ACCOUNT=000000000000
export CDK_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=us-east-1
# Configure CDK to use LocalStack endpoints
export CDK_DEPLOY_ACCOUNT=000000000000
export CDK_DEPLOY_REGION=us-east-1

# Change to infrastructure directory
cd "$(dirname "$0")/../infrastructure"

# Wait for LocalStack to be fully ready
echo "⏳ Waiting for LocalStack to be ready..."
timeout 30 bash -c 'until curl -s http://localhost:4566/_localstack/health | grep -qE "\"sqs\": \"(available|running)\""; do sleep 1; done' || {
    echo "❌ LocalStack health check failed"
    echo "💡 Check LocalStack logs: docker compose logs localstack"
    exit 1
}

# Bootstrap CDK for LocalStack (if needed)
echo "📦 Bootstrapping CDK for LocalStack..."
cdk bootstrap aws://000000000000/us-east-1 \
    --endpoint-url http://localhost:4566 \
    --no-version-reporting \
    || echo "⚠️  Bootstrap may have already completed"

# List available stacks first
echo "📋 Available stacks:"
cdk list

# Deploy stacks with test environment context
# For LocalStack, synthesize and deploy using AWS CLI to avoid CDK asset publishing issues
echo "🏗️  Synthesizing SharedStack..."
cdk synth TaskManagementShared-test \
    --context environment=test \
    --no-version-reporting \
    --quiet || {
    echo "❌ Failed to synthesize SharedStack"
    exit 1
}

# Find the template file in cdk.out
TEMPLATE_FILE=$(find cdk.out -name "*TaskManagementShared-test*.template.json" | head -1)
if [ -z "$TEMPLATE_FILE" ]; then
    echo "❌ Could not find synthesized template file"
    exit 1
fi

echo "📤 Deploying SharedStack to LocalStack using template: $TEMPLATE_FILE"
aws cloudformation deploy \
    --template-file "$TEMPLATE_FILE" \
    --stack-name TaskManagementShared-test \
    --endpoint-url http://localhost:4566 \
    --region us-east-1 \
    --capabilities CAPABILITY_IAM \
    || {
    echo "❌ Failed to deploy SharedStack"
    exit 1
}

# Get stack outputs and format them for tests
echo "📋 Getting stack outputs..."
OUTPUTS_JSON=$(aws cloudformation describe-stacks \
    --stack-name TaskManagementShared-test \
    --endpoint-url http://localhost:4566 \
    --region us-east-1 \
    --query 'Stacks[0].Outputs' \
    --output json)

if [ -n "$OUTPUTS_JSON" ] && [ "$OUTPUTS_JSON" != "null" ]; then
    # Format outputs as expected by tests
    echo "{\"TaskManagementShared-test\": $(echo "$OUTPUTS_JSON" | jq 'map({(.OutputKey): .OutputValue}) | add')}" > ../tests/localstack-outputs.json
    echo "✅ Stack outputs saved"
else
    echo "⚠️  Failed to get stack outputs, but deployment may have succeeded"
fi

echo "✅ Infrastructure deployed successfully!"
echo "📝 Outputs saved to tests/localstack-outputs.json"
