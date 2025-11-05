# LocalStack Testing Guide

This guide explains how to run integration tests using LocalStack with the actual CDK infrastructure.

## Overview

LocalStack provides a local AWS cloud stack that allows testing against real AWS services without deploying to AWS. The tests use the **actual CDK infrastructure code** deployed to LocalStack, ensuring we test the real infrastructure configuration.

## Prerequisites

- Docker and Docker Compose installed
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- LocalStack running (via Docker Compose)

## Quick Start

1. **Start LocalStack**:
   ```bash
   docker-compose up -d
   ```

2. **Deploy CDK infrastructure to LocalStack**:
   ```bash
   ./scripts/setup-localstack-test.sh
   ```

3. **Run LocalStack tests**:
   ```bash
   source venv/bin/activate
   pytest tests/integration/test_localstack.py -v -m localstack
   ```

4. **Cleanup** (optional):
   ```bash
   ./scripts/teardown-localstack-test.sh
   docker-compose down
   ```

## Detailed Workflow

### 1. Start LocalStack

```bash
docker-compose up -d
```

Wait for LocalStack to be ready:
```bash
curl http://localhost:4566/_localstack/health
```

### 2. Deploy Infrastructure

The setup script:
- Bootstraps CDK for LocalStack
- Deploys the SharedStack (SQS FIFO queue, DLQ)
- Saves stack outputs to `tests/localstack-outputs.json`

```bash
./scripts/setup-localstack-test.sh
```

### 3. Run Tests

```bash
# Run all LocalStack tests
pytest tests/integration/test_localstack.py -v -m localstack

# Run specific test
pytest tests/integration/test_localstack.py::TestLocalStackWithCDK::test_end_to_end_with_cdk_infrastructure -v

# Run all tests except LocalStack (faster)
pytest -m "not localstack"
```

### 4. Cleanup

```bash
# Destroy CDK stacks
./scripts/teardown-localstack-test.sh

# Stop LocalStack
docker-compose down
```

## Test Structure

The LocalStack tests:

1. **Use actual CDK infrastructure**: Tests deploy and use the real CDK stacks
2. **Test real SQS behavior**: FIFO ordering, DLQ, deduplication
3. **End-to-end validation**: Full flow from API to queue to processor

## Test Fixtures

Located in `tests/conftest.py`:

- `infrastructure_outputs`: Reads CDK stack outputs (queue URLs, etc.)
- `sqs_client`: Boto3 client configured for LocalStack
- `reset_processed_tasks`: Clears idempotency cache between tests

## Available Tests

- `test_end_to_end_with_cdk_infrastructure`: Full end-to-end flow
- `test_fifo_ordering_with_cdk_queue`: Verifies FIFO ordering
- `test_dlq_functionality_with_cdk_config`: Tests DLQ redrive policy
- `test_idempotency_with_cdk_infrastructure`: Validates idempotent processing

## Troubleshooting

### LocalStack not starting

```bash
# Check Docker is running
docker ps

# Check LocalStack logs
docker-compose logs localstack

# Restart LocalStack
docker-compose restart
```

### CDK deployment fails

```bash
# Check LocalStack health
curl http://localhost:4566/_localstack/health

# Verify environment variables
export AWS_ENDPOINT_URL=http://localhost:4566
export CDK_DEFAULT_ACCOUNT=000000000000
export CDK_DEFAULT_REGION=us-east-1

# Try bootstrap again
cd infrastructure
cdk bootstrap aws://000000000000/us-east-1 --endpoint-url http://localhost:4566
```

### Tests can't find outputs

Make sure you ran the setup script:
```bash
./scripts/setup-localstack-test.sh
```

Check that `tests/localstack-outputs.json` exists.

### Queue URLs not found

Verify the CDK deployment succeeded:
```bash
cd infrastructure
cdk list
cdk synth TaskManagementShared-test
```

## Benefits

1. **Tests actual infrastructure**: Validates CDK code, not mocks
2. **Real AWS behavior**: FIFO ordering, DLQ policies work as in production
3. **Infrastructure validation**: Catches CDK configuration errors
4. **Fast iteration**: No need to deploy to AWS

## Comparison with Moto Tests

- **Moto tests**: Fast, isolated, good for unit testing
- **LocalStack tests**: Slower, more realistic, tests infrastructure code

Use both:
- Moto for unit tests (fast feedback)
- LocalStack for integration tests (realistic validation)
