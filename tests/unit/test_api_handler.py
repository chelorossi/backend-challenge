"""Unit tests for API handler."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.api.handler import create_response, handler


@pytest.fixture
def mock_sqs_client():
    """Mock SQS client."""
    with patch("src.api.handler.sqs_client") as mock_sqs:
        yield mock_sqs


@pytest.fixture
def api_event():
    """Sample API Gateway event."""
    return {
        "httpMethod": "POST",
        "body": json.dumps(
            {
                "title": "Test Task",
                "description": "Test Description",
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
def test_handler_success(mock_sqs_client, api_event, mock_context):
    """Test successful task creation."""
    mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}

    response = handler(api_event, mock_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "task_id" in body
    assert body["message"] == "Task created successfully"

    # Verify SQS message was sent
    mock_sqs_client.send_message.assert_called_once()
    call_args = mock_sqs_client.send_message.call_args
    assert call_args.kwargs["QueueUrl"] == os.environ["QUEUE_URL"]
    assert call_args.kwargs["MessageGroupId"] == "task-processing"
    assert "MessageDeduplicationId" in call_args.kwargs


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_handler_invalid_json(mock_sqs_client, api_event, mock_context):
    """Test handler with invalid JSON."""
    api_event["body"] = "{ invalid json }"

    response = handler(api_event, mock_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body

    # Verify SQS message was not sent
    mock_sqs_client.send_message.assert_not_called()


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_handler_missing_fields(mock_sqs_client, api_event, mock_context):
    """Test handler with missing required fields."""
    api_event["body"] = json.dumps(
        {
            "title": "Test Task"
            # Missing description and priority
        }
    )

    response = handler(api_event, mock_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_handler_sqs_error(mock_sqs_client, api_event, mock_context):
    """Test handler when SQS returns an error."""
    error_response = {
        "Error": {"Code": "ServiceUnavailable", "Message": "Service temporarily unavailable"}
    }
    mock_sqs_client.send_message.side_effect = ClientError(error_response, "SendMessage")

    response = handler(api_event, mock_context)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body


@patch.dict(os.environ, {"QUEUE_URL": ""})
def test_handler_missing_queue_url(api_event, mock_context):
    """Test handler when QUEUE_URL is not configured."""
    response = handler(api_event, mock_context)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body


def test_handler_options_method(api_event, mock_context):
    """Test handler for OPTIONS (CORS preflight) request."""
    api_event["httpMethod"] = "OPTIONS"

    response = handler(api_event, mock_context)

    assert response["statusCode"] == 200
    assert "Access-Control-Allow-Origin" in response["headers"]


def test_handler_invalid_method(api_event, mock_context):
    """Test handler with invalid HTTP method."""
    api_event["httpMethod"] = "GET"

    response = handler(api_event, mock_context)

    assert response["statusCode"] == 405
    body = json.loads(response["body"])
    assert "error" in body


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_handler_dict_body(mock_sqs_client, api_event, mock_context):
    """Test handler when body is already a dict."""
    api_event["body"] = {
        "title": "Test Task",
        "description": "Test Description",
        "priority": "medium",
    }

    mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}

    response = handler(api_event, mock_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "task_id" in body


def test_create_response():
    """Test create_response helper function."""
    body = {"test": "data"}
    headers = {"Custom-Header": "value"}

    response = create_response(200, body, headers)

    assert response["statusCode"] == 200
    assert response["headers"] == headers
    assert json.loads(response["body"]) == body


@patch.dict(
    os.environ, {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue.fifo"}
)
def test_handler_whitespace_sanitization(mock_sqs_client, api_event, mock_context):
    """Test that whitespace is sanitized from request."""
    api_event["body"] = json.dumps(
        {"title": "  Test Task  ", "description": "  Test Description  ", "priority": "low"}
    )

    mock_sqs_client.send_message.return_value = {"MessageId": "test-message-id"}

    response = handler(api_event, mock_context)

    assert response["statusCode"] == 200
    # Verify the message sent to SQS has sanitized values
    call_args = mock_sqs_client.send_message.call_args
    message_body = json.loads(call_args.kwargs["MessageBody"])
    assert message_body["title"] == "Test Task"
    assert message_body["description"] == "Test Description"
