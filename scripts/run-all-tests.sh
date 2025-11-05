#!/bin/bash
# Comprehensive test runner for all test scenarios

set +e  # Don't exit on errors - we want to continue through all scenarios

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Track overall success
OVERALL_SUCCESS=0

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Comprehensive Test Runner${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Function to run tests
run_tests() {
    local test_type=$1
    local description=$2
    local result=0

    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Running: $description${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    case $test_type in
        "unit")
            pytest -m "not localstack" --cov=src --cov-report=term-missing -q || result=1
            ;;
        "integration")
            pytest tests/integration/test_e2e.py --cov=src --cov-report=term-missing -q || result=1
            ;;
        "localstack")
            pytest -m localstack --cov=src --cov-report=term-missing -q || result=1
            ;;
        "all")
            pytest tests/ --cov=src --cov-report=term-missing -q || result=1
            ;;
        *)
            echo "Unknown test type: $test_type"
            return 1
            ;;
    esac

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✅ $description: PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ $description: FAILED${NC}"
        return 1
    fi
}

# Scenario 1: Clean environment - start fresh
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}SCENARIO 1: Clean Environment - Fresh Start${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Stop and remove any existing LocalStack
echo "🧹 Cleaning up existing LocalStack..."
docker compose down -v 2>/dev/null || true
rm -f tests/localstack-outputs.json

# Start LocalStack
echo "🚀 Starting LocalStack..."
docker compose up -d
sleep 5

# Wait for LocalStack to be ready
echo "⏳ Waiting for LocalStack to be ready..."
timeout 30 bash -c 'until curl -s http://localhost:4566/_localstack/health | grep -qE "\"sqs\": \"(available|running)\""; do sleep 1; done' || {
    echo "❌ LocalStack health check failed"
    exit 1
}

# Deploy infrastructure
echo "📦 Deploying infrastructure..."
./scripts/setup-localstack-test.sh

# Run all test types
run_tests "unit" "Unit Tests (clean environment)" || OVERALL_SUCCESS=1
run_tests "integration" "Integration Tests with Mocks (clean environment)" || OVERALL_SUCCESS=1
run_tests "localstack" "LocalStack Tests (clean environment)" || OVERALL_SUCCESS=1
run_tests "all" "All Tests Combined (clean environment)" || OVERALL_SUCCESS=1

# Scenario 2: Reuse infrastructure (no cleanup)
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}SCENARIO 2: Reuse Infrastructure (No Cleanup)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Verify LocalStack is still running
if ! curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then
    echo "❌ LocalStack is not running. Starting it..."
    docker compose up -d
    sleep 5
fi

# Run tests again without redeploying
run_tests "unit" "Unit Tests (reused infrastructure)" || OVERALL_SUCCESS=1
run_tests "integration" "Integration Tests with Mocks (reused infrastructure)" || OVERALL_SUCCESS=1
run_tests "localstack" "LocalStack Tests (reused infrastructure)" || OVERALL_SUCCESS=1
run_tests "all" "All Tests Combined (reused infrastructure)" || OVERALL_SUCCESS=1

# Scenario 3: Clean teardown and fresh start
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}SCENARIO 3: Clean Teardown and Fresh Start${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Teardown infrastructure
echo "🗑️  Tearing down infrastructure..."
./scripts/teardown-localstack-test.sh

# Clean up LocalStack
echo "🧹 Cleaning up LocalStack..."
docker compose down -v
rm -f tests/localstack-outputs.json

# Start fresh
echo "🚀 Starting fresh LocalStack..."
docker compose up -d
sleep 5

# Wait for LocalStack to be ready
echo "⏳ Waiting for LocalStack to be ready..."
timeout 30 bash -c 'until curl -s http://localhost:4566/_localstack/health | grep -qE "\"sqs\": \"(available|running)\""; do sleep 1; done' || {
    echo "❌ LocalStack health check failed"
    exit 1
}

# Deploy infrastructure again
echo "📦 Deploying infrastructure..."
./scripts/setup-localstack-test.sh

# Run all tests again
run_tests "unit" "Unit Tests (after teardown and fresh start)" || OVERALL_SUCCESS=1
run_tests "integration" "Integration Tests with Mocks (after teardown and fresh start)" || OVERALL_SUCCESS=1
run_tests "localstack" "LocalStack Tests (after teardown and fresh start)" || OVERALL_SUCCESS=1
run_tests "all" "All Tests Combined (after teardown and fresh start)" || OVERALL_SUCCESS=1

# Final summary
echo ""
if [ $OVERALL_SUCCESS -eq 0 ]; then
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✅ All Test Scenarios Completed Successfully!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
else
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  ⚠️  Some Tests Failed${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
fi
echo ""
echo "Test Summary:"
echo "  - Scenario 1: Clean environment"
echo "  - Scenario 2: Reused infrastructure"
echo "  - Scenario 3: Teardown and fresh start"
echo ""
if [ $OVERALL_SUCCESS -eq 0 ]; then
    echo "All tests are passing and the infrastructure can be deployed and"
    echo "torn down reliably!"
    exit 0
else
    echo "Some tests failed. Please review the output above."
    exit 1
fi
