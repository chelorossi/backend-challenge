"""Lambda handler for task management API."""

import json
import logging
import os
import uuid
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from .models import TaskResponse
from .validators import validate_task_request

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SQS client
sqs_client = boto3.client("sqs")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /tasks endpoint.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return create_response(
            200,
            {},
            {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-Amz-Date, Authorization, X-Api-Key",
            },
        )

    # Only allow POST method
    if event.get("httpMethod") != "POST":
        return create_response(
            405,
            {"error": "Method not allowed"},
            {"Access-Control-Allow-Origin": "*"},
        )

    # Get queue URL from environment (read at runtime for testing)
    queue_url = os.environ.get("QUEUE_URL")

    # Check if queue URL is configured
    if not queue_url:
        logger.error("QUEUE_URL environment variable is not set")
        return create_response(
            500,
            {"error": "Server configuration error"},
            {"Access-Control-Allow-Origin": "*"},
        )

    # Get request body
    body = event.get("body", "")
    if isinstance(body, dict):
        body = json.dumps(body)

    # Validate request
    task, error_message, status_code = validate_task_request(body)
    if task is None:
        logger.warning(f"Validation failed: {error_message}")
        return create_response(
            status_code,
            {"error": error_message},
            {"Access-Control-Allow-Origin": "*"},
        )

    # Generate unique task ID
    task_id = str(uuid.uuid4())

    # Prepare message for SQS
    message_body = {
        "task_id": task_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority.value,
        "due_date": task.due_date,
    }

    # Send message to SQS FIFO queue
    try:
        # Use MessageGroupId for FIFO ordering - using a single group for strict ordering
        # Use MessageDeduplicationId to prevent duplicates
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
            MessageGroupId="task-processing",  # Single group for strict FIFO ordering
            MessageDeduplicationId=task_id,  # Use task_id for deduplication
        )

        logger.info(f"Task {task_id} sent to queue. MessageId: {response.get('MessageId')}")

        # Return success response
        task_response = TaskResponse(task_id=task_id)
        return create_response(
            200,
            task_response.model_dump(),
            {"Access-Control-Allow-Origin": "*"},
        )

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Failed to send message to SQS: {error_code} - {error_message}")
        return create_response(
            500,
            {"error": "Failed to queue task for processing"},
            {"Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_response(
            500,
            {"error": "Internal server error"},
            {"Access-Control-Allow-Origin": "*"},
        )


def create_response(
    status_code: int, body: Dict[str, Any], headers: Dict[str, str]
) -> Dict[str, Any]:
    """
    Create API Gateway response.

    Args:
        status_code: HTTP status code
        body: Response body
        headers: Response headers

    Returns:
        API Gateway response format
    """
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body),
    }
