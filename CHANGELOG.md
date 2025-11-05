# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-01-XX

### Added

- **LocalStack integration** for comprehensive integration testing
  - Full CDK infrastructure deployment to LocalStack
  - End-to-end tests using actual AWS services locally
  - Comprehensive test coverage including error paths
  - Test automation scripts for setup and teardown
- **Enhanced test coverage** - All tests including LocalStack tests achieve 90%+ coverage
- **Comprehensive test runner** script (`scripts/run-all-tests.sh`) for validating all test scenarios
- **Improved error handling** tests for API and processor handlers
- **CORS preflight** support testing
- **Idempotency testing** with LocalStack infrastructure

### Changed

- Test infrastructure now supports both mocked (moto) and LocalStack-based testing
- Improved teardown script to use AWS CLI for reliable stack deletion
- Enhanced error path coverage in integration tests

### Technical Details

- LocalStack tests use the same CDK infrastructure as production
- Tests validate FIFO queue ordering, DLQ functionality, and retry mechanisms
- All tests meet the 90% code coverage requirement per challenge specifications

## [1.0.0] - 2024-01-XX

### Added

- Initial release
- AWS CDK infrastructure (SharedStack, ApiStack, ProcessingStack)
- REST API endpoint for task creation (POST /tasks)
- SQS FIFO queue with content-based deduplication
- Background task processor with retry logic
- Dead Letter Queue (DLQ) for failed messages
- CloudWatch logging and monitoring
- Unit tests with mocks
- Integration tests with moto
- Code quality tools (Black, Pyright)
- Comprehensive test coverage (90%+)
