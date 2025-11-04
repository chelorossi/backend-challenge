"""Lambda handler for processing tasks from SQS queue."""

import json
import logging
import os
from typing import Any, Dict

from .task_processor import PermanentError, TaskProcessingError, TransientError, process_task

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get environment variables
DLQ_URL = os.environ.get("DLQ_URL")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

# Track processed task IDs for idempotency (in production, use DynamoDB or similar)
# This is a simple in-memory cache for demonstration
# In production, use a distributed cache like DynamoDB or Redis
_processed_tasks: set[str] = set()  # Exported for testing purposes


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing SQS messages.

    Args:
        event: SQS event containing messages
        context: Lambda context

    Returns:
        Response with batch item failures if any
    """
    logger.info(f"Received SQS event with {len(event.get('Records', []))} records")

    batch_item_failures: list[Dict[str, str]] = []

    for record in event.get("Records", []):
        message_id = record.get("messageId")
        receipt_handle = record.get("receiptHandle")
        body = record.get("body", "")

        try:
            # Parse message body
            try:
                task_data = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in message {message_id}: {str(e)}")
                # This is a permanent error - don't retry
                continue

            task_id = task_data.get("task_id")
            if not task_id:
                logger.error(f"Missing task_id in message {message_id}")
                # This is a permanent error - don't retry
                continue

            # Check for idempotency (prevent duplicate processing)
            if is_already_processed(task_id):
                logger.info(f"Task {task_id} already processed - skipping (idempotency)")
                continue

            # Process the task
            try:
                process_task(task_data)
                # Mark as processed
                mark_as_processed(task_id)
                logger.info(f"Successfully processed task {task_id}")

            except TransientError as e:
                # Transient error - should retry
                logger.warning(f"Transient error processing task {task_id}: {str(e)}")
                batch_item_failures.append({"itemIdentifier": message_id})

            except PermanentError as e:
                # Permanent error - should not retry, send to DLQ
                logger.error(f"Permanent error processing task {task_id}: {str(e)}")
                # Don't add to batch_item_failures - let it go to DLQ after maxReceiveCount

            except Exception as e:
                # Unexpected error - treat as transient for retry
                logger.error(f"Unexpected error processing task {task_id}: {str(e)}", exc_info=True)
                batch_item_failures.append({"itemIdentifier": message_id})

        except Exception as e:
            # Error processing the record itself - treat as transient
            logger.error(f"Error processing record {message_id}: {str(e)}", exc_info=True)
            batch_item_failures.append({"itemIdentifier": message_id})

    # Return batch item failures for partial batch response
    response: Dict[str, Any] = {}
    if batch_item_failures:
        response["batchItemFailures"] = batch_item_failures
        logger.info(f"Returning {len(batch_item_failures)} batch item failures for retry")

    return response


def is_already_processed(task_id: str) -> bool:
    """
    Check if a task has already been processed (idempotency check).

    Args:
        task_id: Task identifier

    Returns:
        True if task has been processed, False otherwise

    Note:
        In production, this should use a distributed cache like DynamoDB
        to handle concurrent processing across multiple Lambda instances.
    """
    return task_id in _processed_tasks


def mark_as_processed(task_id: str) -> None:
    """
    Mark a task as processed.

    Args:
        task_id: Task identifier

    Note:
        In production, this should use a distributed cache like DynamoDB
        to handle concurrent processing across multiple Lambda instances.
    """
    _processed_tasks.add(task_id)
    # In production, also set TTL to prevent unbounded growth
