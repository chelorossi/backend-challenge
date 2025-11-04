"""Unit tests for processor handler."""

import json
import os
from unittest.mock import patch

import pytest

from src.processor.handler import (
    _processed_tasks,
    handler,
    is_already_processed,
    mark_as_processed,
)
from src.processor.task_processor import (
    PermanentError,
    TaskProcessingError,
    TransientError,
    process_task,
)


@pytest.fixture(autouse=True)
def clear_processed_tasks():
    """Clear processed tasks before each test."""
    _processed_tasks.clear()
    yield
    _processed_tasks.clear()


@pytest.fixture
def sqs_event():
    """Sample SQS event."""
    return {
        "Records": [
            {
                "messageId": "test-message-id-1",
                "receiptHandle": "test-receipt-handle-1",
                "body": json.dumps(
                    {
                        "task_id": "test-task-id-1",
                        "title": "Test Task 1",
                        "description": "Test Description 1",
                        "priority": "high",
                        "due_date": "2024-12-31T23:59:59Z",
                    }
                ),
                "attributes": {"ApproximateReceiveCount": "1"},
            }
        ]
    }


@pytest.fixture
def mock_context():
    """Mock Lambda context."""
    context = type(
        "Context", (), {"function_name": "test-processor", "aws_request_id": "test-request-id"}
    )()
    return context


def test_process_task_success():
    """Test successful task processing."""
    task_data = {
        "task_id": "test-task-id",
        "title": "Test Task",
        "description": "Test Description",
        "priority": "high",
    }

    # Should not raise any exception
    process_task(task_data)


def test_process_task_transient_error():
    """Test task processing with transient error."""
    task_data = {
        "task_id": "test-task-id",
        "title": "__SIMULATE_TRANSIENT_ERROR__",
        "description": "Test Description",
        "priority": "medium",
    }

    with pytest.raises(TransientError):
        process_task(task_data)


def test_process_task_permanent_error():
    """Test task processing with permanent error."""
    task_data = {
        "task_id": "test-task-id",
        "title": "__SIMULATE_PERMANENT_ERROR__",
        "description": "Test Description",
        "priority": "low",
    }

    with pytest.raises(PermanentError):
        process_task(task_data)


def test_handler_success(sqs_event, mock_context):
    """Test successful message processing."""
    response = handler(sqs_event, mock_context)

    assert "batchItemFailures" not in response or len(response.get("batchItemFailures", [])) == 0


def test_handler_transient_error(sqs_event, mock_context):
    """Test handler with transient error (should retry)."""
    sqs_event["Records"][0]["body"] = json.dumps(
        {
            "task_id": "test-task-id-1",
            "title": "__SIMULATE_TRANSIENT_ERROR__",
            "description": "Test Description",
            "priority": "high",
        }
    )

    response = handler(sqs_event, mock_context)

    assert "batchItemFailures" in response
    assert len(response["batchItemFailures"]) == 1
    assert response["batchItemFailures"][0]["itemIdentifier"] == "test-message-id-1"


def test_handler_permanent_error(sqs_event, mock_context):
    """Test handler with permanent error (should not retry)."""
    sqs_event["Records"][0]["body"] = json.dumps(
        {
            "task_id": "test-task-id-1",
            "title": "__SIMULATE_PERMANENT_ERROR__",
            "description": "Test Description",
            "priority": "high",
        }
    )

    response = handler(sqs_event, mock_context)

    # Permanent errors should not be in batch_item_failures
    # They will go to DLQ after maxReceiveCount
    assert "batchItemFailures" not in response or len(response.get("batchItemFailures", [])) == 0


def test_handler_invalid_json(sqs_event, mock_context):
    """Test handler with invalid JSON in message."""
    sqs_event["Records"][0]["body"] = "{ invalid json }"

    response = handler(sqs_event, mock_context)

    # Invalid JSON is a permanent error - don't retry
    assert "batchItemFailures" not in response or len(response.get("batchItemFailures", [])) == 0


def test_handler_missing_task_id(sqs_event, mock_context):
    """Test handler with missing task_id."""
    sqs_event["Records"][0]["body"] = json.dumps(
        {"title": "Test Task", "description": "Test Description", "priority": "high"}
    )

    response = handler(sqs_event, mock_context)

    # Missing task_id is a permanent error - don't retry
    assert "batchItemFailures" not in response or len(response.get("batchItemFailures", [])) == 0


def test_handler_idempotency(sqs_event, mock_context):
    """Test that handler processes same task only once."""
    task_id = "test-task-id-duplicate"

    # First processing
    sqs_event["Records"][0]["body"] = json.dumps(
        {
            "task_id": task_id,
            "title": "Test Task",
            "description": "Test Description",
            "priority": "high",
        }
    )

    response1 = handler(sqs_event, mock_context)
    assert "batchItemFailures" not in response1 or len(response1.get("batchItemFailures", [])) == 0

    # Second processing of same task (should be skipped)
    response2 = handler(sqs_event, mock_context)
    assert "batchItemFailures" not in response2 or len(response2.get("batchItemFailures", [])) == 0


def test_handler_multiple_records(sqs_event, mock_context):
    """Test handler with multiple records."""
    sqs_event["Records"].append(
        {
            "messageId": "test-message-id-2",
            "receiptHandle": "test-receipt-handle-2",
            "body": json.dumps(
                {
                    "task_id": "test-task-id-2",
                    "title": "Test Task 2",
                    "description": "Test Description 2",
                    "priority": "medium",
                }
            ),
            "attributes": {"ApproximateReceiveCount": "1"},
        }
    )

    response = handler(sqs_event, mock_context)

    assert "batchItemFailures" not in response or len(response.get("batchItemFailures", [])) == 0


def test_handler_mixed_errors(sqs_event, mock_context):
    """Test handler with mixed success and error records."""
    sqs_event["Records"].append(
        {
            "messageId": "test-message-id-2",
            "receiptHandle": "test-receipt-handle-2",
            "body": json.dumps(
                {
                    "task_id": "test-task-id-2",
                    "title": "__SIMULATE_TRANSIENT_ERROR__",
                    "description": "Test Description 2",
                    "priority": "medium",
                }
            ),
            "attributes": {"ApproximateReceiveCount": "1"},
        }
    )

    response = handler(sqs_event, mock_context)

    # Should have one batch item failure
    assert "batchItemFailures" in response
    assert len(response["batchItemFailures"]) == 1
    assert response["batchItemFailures"][0]["itemIdentifier"] == "test-message-id-2"


def test_handler_empty_records(mock_context):
    """Test handler with empty records."""
    sqs_event = {"Records": []}

    response = handler(sqs_event, mock_context)

    assert "batchItemFailures" not in response or len(response.get("batchItemFailures", [])) == 0


def test_handler_unexpected_exception(sqs_event, mock_context):
    """Test handler with unexpected exception."""
    with patch("src.processor.handler.process_task") as mock_process:
        mock_process.side_effect = Exception("Unexpected error")

        response = handler(sqs_event, mock_context)

        # Unexpected errors should be retried
        assert "batchItemFailures" in response
        assert len(response["batchItemFailures"]) == 1


def test_is_already_processed():
    """Test idempotency check."""
    task_id = "test-task-id-new"

    assert not is_already_processed(task_id)

    mark_as_processed(task_id)

    assert is_already_processed(task_id)


def test_mark_as_processed():
    """Test marking task as processed."""
    task_id = "test-task-id-mark"

    assert not is_already_processed(task_id)

    mark_as_processed(task_id)

    assert is_already_processed(task_id)
