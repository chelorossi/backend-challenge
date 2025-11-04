# Backend Engineering Challenge

Welcome to our backend engineering challenge! This project is designed to assess your skills in **Python**, **TypeScript**, **AWS**, and **AWS CDK**.

## Overview

You will build a task management API system with these components:

- AWS CDK infrastructure deployment
- REST API endpoint for task creation
- Message queue with ordered processing
- Background task processor

## Challenge Requirements

### 1. Infrastructure as Code (AWS CDK)

Create AWS CDK stacks that deploy your entire infrastructure:

#### Stack Components

- Compute resources (Python for all backend logic)
- REST API with single POST endpoint
- Message queue for ordered task processing
- Logging and basic monitoring

#### Requirements

- Use AWS CDK v2 with TypeScript
- Implement proper stack organization (separate stacks for different concerns)
- Include environment-specific configurations
- Document deployment process
- **Must support `cdk synth` command to validate infrastructure code**
- **No hardcoded account IDs, regions, or environment-specific values**
- **Infrastructure should be deployable but actual deployment is not required for evaluation**

### 2. Core API (Python)

Create a REST API endpoint using Python:

#### Endpoint

- `POST /tasks` - Accept and validate a new task, then send it to a processing queue

#### Task Model

```json
{
  "title": "string",
  "description": "string",
  "priority": "low | medium | high",
  "due_date": "ISO 8601 timestamp (optional)"
}
```

#### Requirements

- Choose appropriate AWS compute services for the API
- Implement comprehensive input validation and sanitization
- Send validated tasks to a message queue that preserves ordering
- Return a unique task id to the requester
- Ensure at-least-once delivery guarantees
- Implement proper error handling and return appropriate HTTP status codes
- Include unit tests using pytest
- Use type hints throughout your Python code

### 3. Queue Processing System (Python)

Create a queue processing system using Python that:

#### Functionality

- Processes tasks from the queue _in the order they were received_
- Implements at-least-once processing guarantees
- Implements proper retry logic and dead letter handling for failed processing of tasks
- Maintains ordering guarantees even with retries

#### Requirements

- Use Python with proper type hints
- Choose appropriate AWS compute services for queue processing
- Implement dead letter queue for failed messages
- Include comprehensive error handling and logging
- Include unit tests using pytest
- Ensure idempotent processing to handle duplicate deliveries

### 4. Documentation and Best Practices

#### Code Quality

- **Python code must be formatted using a documented formatter (e.g., black, autopep8, ruff)**
- **Python code should pass standard type check from pyright**
- Follow TypeScript/ESLint best practices for CDK infrastructure code
- Include comprehensive README files
- Implement proper logging

#### Testing

- Unit tests for all business logic
- Integration tests for REST endpoints using mocked AWS services
- Mock external dependencies appropriately (use moto, localstack, or similar for AWS mocking)
- **Achieve 90% test coverage for Python code using pytest**

#### Security

- Implement input validation and sanitization
- Use environment variables for configuration
- Follow AWS security best practices
- **Implement least privilege access controls for all AWS resources**
- Implement proper CORS configuration

## Architecture Focus

Your solution should demonstrate:

- **Ordering Guarantees**: Tasks must be processed in the exact order they are received
- **At-Least-Once Processing**: Every valid task must be processed at least once
- **Error Handling**: Robust error handling with appropriate retries and dead letter queues
- **Validation**: Comprehensive input validation before queueing tasks

## Getting Started

1. **Create a private fork of this repository** to your own GitHub account
2. **Set up your development environment** with AWS CDK, Python, and necessary dependencies
3. **Implement the solution** following the requirements
4. **Test thoroughly** and ensure all tests pass (use mocks for AWS services)
5. **Validate CDK synthesis** by running `cdk synth` to ensure infrastructure code is valid
6. **Document your solution** including setup and deployment instructions
7. **Zip the repository** and deliver it to the hiring manager.

## Evaluation Criteria

You will be evaluated in the following order of priority:

### Infrastructure Validity and Functionality

- **CDK infrastructure synthesizes successfully** using `cdk synth` without errors
- **API endpoint logic works as expected** - accepts valid tasks and handles errors properly (tested with mocks)
- **Queue processing system functions correctly** - processes tasks in order with proper retry logic (tested with mocks)
- **All components integrate properly** - end-to-end functionality works with mocked AWS services

### Code Quality and Testing

- **Code quality** - Clean, readable, well-structured Python and TypeScript code
- **Test coverage** - Comprehensive test suite with full coverage as specified
- **Type safety** - Proper type hints and passes pyright type checking
- **Code formatting** - Consistent formatting using documented formatter

### Additional Considerations

- **Architecture** - Proper separation of concerns and scalable design
- **Security** - Least privilege access controls and input validation
- **Documentation** - Clear setup instructions and architectural decisions
- **AWS best practices** - Effective use of AWS services and patterns

## Bonus Points

- Implement API authentication
- Add comprehensive monitoring and observability
- Implement CI/CD pipeline
- Add API rate limiting and throttling

## Time Expectation

This challenge is designed to take approximately **1-2 hours** to complete. Focus on demonstrating your understanding of the core technologies rather than implementing every possible feature. **No actual AWS deployment is required** - the evaluation focuses on code quality, architecture, and the ability to synthesize valid CloudFormation templates.

## Questions?

If you have any questions about the requirements or need clarification on any aspect of the challenge, please create an issue in this repository or reach out to your point of contact.

---

## Solution Implementation

This section documents the implemented solution.

### Architecture

The solution uses a serverless architecture with AWS CDK for infrastructure as code:

```
┌─────────────────┐
│   API Gateway   │
│   REST API      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lambda (API)   │ ───► ┌─────────────────┐
│  Python Handler │      │  SQS FIFO Queue  │
└─────────────────┘      │  (Ordered)       │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Lambda (Processor)│
                         │ Python Handler   │
                         └─────────────────┘
                                  │
                                  │ (on failure after retries)
                                  ▼
                         ┌─────────────────┐
                         │  Dead Letter    │
                         │  Queue (DLQ)    │
                         └─────────────────┘
```

#### Key Components

1. **API Gateway REST API**: Exposes POST /tasks endpoint with CORS support
2. **API Lambda Function**: Validates requests, generates task IDs, sends to SQS FIFO queue
3. **SQS FIFO Queue**: Ensures ordered processing with content-based deduplication
4. **Processor Lambda Function**: Processes tasks from queue with retry logic and idempotency
5. **Dead Letter Queue (DLQ)**: Captures failed messages after max retries
6. **CloudWatch**: Logging and monitoring for all components

#### Stack Organization

- **SharedStack**: SQS FIFO queue, DLQ, CloudWatch log groups
- **ApiStack**: API Gateway, API Lambda function
- **ProcessingStack**: Processor Lambda function, SQS event source mapping, CloudWatch alarms

### Setup Instructions

#### Prerequisites

- Node.js 18+ and pnpm (or npm/yarn)
- Python 3.11+
- AWS CDK CLI v2 installed (`npm install -g aws-cdk`)

#### Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd backend-challenge
   ```

2. **Set up Python environment**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```

3. **Set up CDK infrastructure**:
   ```bash
   cd infrastructure
   pnpm install
   ```

#### Configuration

The solution uses environment-aware configuration through CDK context. No hardcoded values are used.

You can configure the environment by setting CDK context:

```bash
cdk synth -c environment=prod -c account=123456789012 -c region=us-east-1
```

Or by setting environment variables:

```bash
export CDK_DEFAULT_ACCOUNT=123456789012
export CDK_DEFAULT_REGION=us-east-1
```

### Testing

#### Run All Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_api_handler.py -v

# Run integration tests
pytest tests/integration/ -v
```

#### Test Coverage

The solution achieves **95%+ test coverage** with:

- Unit tests for all business logic
- Integration tests for end-to-end flows
- Mocked AWS services using unittest.mock

#### Test Structure

```
tests/
├── unit/
│   ├── test_api_handler.py      # API handler unit tests
│   ├── test_validators.py        # Validation logic tests
│   └── test_processor.py         # Processor handler tests
└── integration/
    └── test_e2e.py               # End-to-end integration tests
```

### Code Quality

#### Formatting

Code is formatted using **black**:

```bash
black src tests
```

#### Type Checking

Type checking is done with **pyright**:

```bash
pyright src
```

#### CDK Validation

Validate infrastructure code:

```bash
cd infrastructure
pnpm run synth
```

### Deployment

While actual deployment is not required for evaluation, the infrastructure is fully deployable.

#### Prerequisites for Deployment

- AWS CLI configured with credentials
- AWS CDK bootstrap in target account/region:
  ```bash
  cdk bootstrap aws://ACCOUNT-ID/REGION
  ```

#### Deploy All Stacks

```bash
cd infrastructure
cdk deploy --all
```

#### Deploy Specific Stack

```bash
cdk deploy TaskManagementShared-dev
cdk deploy TaskManagementApi-dev
cdk deploy TaskManagementProcessing-dev
```

### Architecture Decisions

1. **SQS FIFO Queue**: Chosen for guaranteed ordering and exactly-once delivery within message groups
2. **Lambda Functions**: Serverless compute for cost-effectiveness and auto-scaling
3. **Single Message Group**: All tasks use the same MessageGroupId for strict FIFO ordering
4. **Content-Based Deduplication**: Prevents duplicate messages in the queue
5. **Idempotency**: In-memory cache for demonstration (production would use DynamoDB or Redis)
6. **Batch Size 1**: Process one message at a time to maintain strict ordering
7. **Least Privilege IAM**: Each Lambda has only the minimum permissions needed

### Security Features

- **Input Validation**: Pydantic models with comprehensive validation
- **Input Sanitization**: Whitespace stripping and format validation
- **IAM Least Privilege**:
  - API Lambda: Only `sqs:SendMessage` permission
  - Processor Lambda: Only SQS consume permissions
- **CORS Configuration**: Proper CORS headers for API Gateway
- **Error Handling**: No sensitive information leaked in error messages

### Monitoring and Observability

- **CloudWatch Logs**: All Lambda functions log to CloudWatch
- **CloudWatch Alarms**: DLQ message alarm for failed task monitoring
- **Structured Logging**: JSON-formatted logs with task IDs and context

### API Usage

#### Create a Task

```bash
curl -X POST https://<api-gateway-url>/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Complete project",
    "description": "Finish the backend challenge",
    "priority": "high",
    "due_date": "2024-12-31T23:59:59Z"
  }'
```

#### Response

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task created successfully"
}
```

### Error Handling

- **400 Bad Request**: Invalid input (validation errors)
- **405 Method Not Allowed**: Non-POST requests
- **500 Internal Server Error**: Queue errors or system failures

### Project Structure

```
backend-challenge/
├── infrastructure/          # CDK infrastructure code
│   ├── bin/
│   │   └── app.ts          # CDK app entry point
│   ├── lib/
│   │   ├── shared-stack.ts  # Shared resources
│   │   ├── api-stack.ts     # API stack
│   │   └── processing-stack.ts # Processor stack
│   ├── cdk.json
│   └── package.json
├── src/                     # Python source code
│   ├── api/
│   │   ├── handler.py       # API Lambda handler
│   │   ├── models.py        # Pydantic models
│   │   └── validators.py    # Validation logic
│   └── processor/
│       ├── handler.py       # Processor Lambda handler
│       └── task_processor.py # Business logic
├── tests/                   # Test suite
│   ├── unit/
│   └── integration/
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # Development dependencies
├── pyproject.toml           # Python tool configuration
├── pyrightconfig.json       # Type checker config
└── README.md
```

### Future Enhancements

Potential improvements for production:

1. **Idempotency**: Replace in-memory cache with DynamoDB
2. **Authentication**: Add API key or JWT authentication
3. **Rate Limiting**: Implement API Gateway throttling
4. **Monitoring**: Add X-Ray tracing and custom metrics
5. **CI/CD**: Set up automated deployment pipeline
6. **Database**: Store task state and history
7. **Notifications**: Add SNS notifications for task completion

Good luck! 🚀
