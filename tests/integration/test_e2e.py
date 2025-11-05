"""Integration tests for end-to-end flow."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.api.handler import handler as api_handler
from src.processor.handler import handler as processor_handler


@pytest.fixture
def mock_sqs_client():
    """Mock SQS client for API."""
    with patch("src.api.handler.get_sqs_client") as mock_get_client:
        mock_sqs = MagicMock()
        mock_get_client.return_value = mock_sqs
        yield mock_sqs


@pytest.fixture
def api_event():
    """Sample API Gateway event."""
    return {
        "httpMethod": "POST",
        "body": json.dumps(
            {
                "title": "Integration Test Task",
                "description": "Integration test description",
                "priority": "high",
                "due_date": "2024-12-31T23:59:59Z",
            }
        ),
        "headers": {"Content-Type": "application/json"},
    }


@pytest.fixture
def mock_context():
    """Mock Lambda context."""
    context = MagicMock()
    context.function_name = "test-function"
    context.aws_request_id = "test-request-id"
    return context


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_end_to_end_success(mock_sqs_client, api_event, mock_context):
    """Test end-to-end flow: API creates task, processor processes it."""
    # Step 1: API receives request and sends to SQS
    mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}

    api_response = api_handler(api_event, mock_context)

    assert api_response["statusCode"] == 200
    api_body = json.loads(api_response["body"])
    task_id = api_body["task_id"]

    # Verify message was sent to SQS
    assert mock_sqs_client.send_message.called
    call_args = mock_sqs_client.send_message.call_args
    message_body = json.loads(call_args.kwargs["MessageBody"])
    assert message_body["task_id"] == task_id

    # Step 2: Processor receives message from SQS
    sqs_event = {
        "Records": [
            {
                "messageId": "test-message-id",
                "receiptHandle": "test-receipt-handle",
                "body": call_args.kwargs["MessageBody"],
                "attributes": {"ApproximateReceiveCount": "1"},
            }
        ]
    }

    processor_response = processor_handler(sqs_event, mock_context)

    # Should process successfully
    assert (
        "batchItemFailures" not in processor_response
        or len(processor_response.get("batchItemFailures", [])) == 0
    )


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_end_to_end_validation_error(mock_sqs_client, api_event, mock_context):
    """Test end-to-end flow with validation error."""
    # Invalid request (missing required fields)
    api_event["body"] = json.dumps(
        {
            "title": "Test Task"
            # Missing description and priority
        }
    )

    api_response = api_handler(api_event, mock_context)

    assert api_response["statusCode"] == 400
    api_body = json.loads(api_response["body"])
    assert "error" in api_body

    # Verify message was NOT sent to SQS
    mock_sqs_client.send_message.assert_not_called()


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_end_to_end_retry_scenario(mock_sqs_client, api_event, mock_context):
    """Test end-to-end flow with retry scenario (transient error)."""
    # Step 1: API creates task
    mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}

    api_response = api_handler(api_event, mock_context)
    assert api_response["statusCode"] == 200

    # Step 2: Processor receives message with transient error
    call_args = mock_sqs_client.send_message.call_args
    message_body = json.loads(call_args.kwargs["MessageBody"])
    message_body["title"] = "__SIMULATE_TRANSIENT_ERROR__"  # Simulate transient error

    sqs_event = {
        "Records": [
            {
                "messageId": "test-message-id",
                "receiptHandle": "test-receipt-handle",
                "body": json.dumps(message_body),
                "attributes": {"ApproximateReceiveCount": "1"},
            }
        ]
    }

    processor_response = processor_handler(sqs_event, mock_context)

    # Should request retry
    assert "batchItemFailures" in processor_response
    assert len(processor_response["batchItemFailures"]) == 1


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_end_to_end_dlq_scenario(mock_sqs_client, api_event, mock_context):
    """Test end-to-end flow with DLQ scenario (permanent error)."""
    # Step 1: API creates task
    mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}

    api_response = api_handler(api_event, mock_context)
    assert api_response["statusCode"] == 200

    # Step 2: Processor receives message with permanent error
    call_args = mock_sqs_client.send_message.call_args
    message_body = json.loads(call_args.kwargs["MessageBody"])
    message_body["title"] = "__SIMULATE_PERMANENT_ERROR__"  # Simulate permanent error

    sqs_event = {
        "Records": [
            {
                "messageId": "test-message-id",
                "receiptHandle": "test-receipt-handle",
                "body": json.dumps(message_body),
                "attributes": {"ApproximateReceiveCount": "3"},  # Max retries reached
            }
        ]
    }

    processor_response = processor_handler(sqs_event, mock_context)

    # Permanent errors should not be in batch_item_failures
    # They will go to DLQ after maxReceiveCount
    assert (
        "batchItemFailures" not in processor_response
        or len(processor_response.get("batchItemFailures", [])) == 0
    )


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_end_to_end_idempotency(mock_sqs_client, api_event, mock_context):
    """Test end-to-end flow with idempotency (duplicate processing)."""
    # Step 1: API creates task
    mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}

    api_response = api_handler(api_event, mock_context)
    assert api_response["statusCode"] == 200

    # Step 2: Processor processes message first time
    call_args = mock_sqs_client.send_message.call_args
    message_body = json.loads(call_args.kwargs["MessageBody"])
    task_id = message_body["task_id"]

    sqs_event = {
        "Records": [
            {
                "messageId": "test-message-id-1",
                "receiptHandle": "test-receipt-handle-1",
                "body": json.dumps(message_body),
                "attributes": {"ApproximateReceiveCount": "1"},
            }
        ]
    }

    processor_response1 = processor_handler(sqs_event, mock_context)
    assert (
        "batchItemFailures" not in processor_response1
        or len(processor_response1.get("batchItemFailures", [])) == 0
    )

    # Step 3: Processor receives same message again (duplicate)
    sqs_event["Records"][0]["messageId"] = "test-message-id-2"
    processor_response2 = processor_handler(sqs_event, mock_context)

    # Should skip processing (idempotency)
    assert (
        "batchItemFailures" not in processor_response2
        or len(processor_response2.get("batchItemFailures", [])) == 0
    )


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_end_to_end_multiple_tasks(mock_sqs_client, api_event, mock_context):
    """Test end-to-end flow with multiple tasks."""
    # Create multiple tasks
    task_ids = []
    for i in range(3):
        api_event["body"] = json.dumps(
            {"title": f"Task {i}", "description": f"Description {i}", "priority": "medium"}
        )

        mock_sqs_client.send_message.return_value = {"MessageId": f"test-message-id-{i}"}
        api_response = api_handler(api_event, mock_context)

        assert api_response["statusCode"] == 200
        api_body = json.loads(api_response["body"])
        task_ids.append(api_body["task_id"])

    # Process all tasks
    records = []
    for i, task_id in enumerate(task_ids):
        call_args = mock_sqs_client.send_message.call_args_list[i]
        message_body = json.loads(call_args.kwargs["MessageBody"])

        records.append(
            {
                "messageId": f"test-message-id-{i}",
                "receiptHandle": f"test-receipt-handle-{i}",
                "body": json.dumps(message_body),
                "attributes": {"ApproximateReceiveCount": "1"},
            }
        )

    sqs_event = {"Records": records}
    processor_response = processor_handler(sqs_event, mock_context)

    # All tasks should process successfully
    assert (
        "batchItemFailures" not in processor_response
        or len(processor_response.get("batchItemFailures", [])) == 0
    )
