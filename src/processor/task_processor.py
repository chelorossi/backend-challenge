"""Core task processing business logic."""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TaskProcessingError(Exception):
    """Base exception for task processing errors."""

    pass


class TransientError(TaskProcessingError):
    """Transient error that should be retried."""

    pass


class PermanentError(TaskProcessingError):
    """Permanent error that should not be retried."""

    pass


def process_task(task_data: Dict[str, Any]) -> None:
    """
    Process a single task.

    This is the core business logic for task processing.
    In a real application, this would perform the actual task processing.

    Args:
        task_data: Task data dictionary containing task_id, title, description, priority, due_date

    Raises:
        TransientError: For errors that should be retried (e.g., network timeouts)
        PermanentError: For errors that should not be retried (e.g., invalid data)
    """
    task_id = task_data.get("task_id")
    title = task_data.get("title")
    priority = task_data.get("priority", "medium")

    logger.info(f"Processing task {task_id}: {title} (priority: {priority})")

    # Simulate task processing
    # In a real application, this would:
    # - Save to database
    # - Send notifications
    # - Update external systems
    # - etc.

    # Example: Simulate processing based on priority
    if priority == "high":
        logger.info(f"High priority task {task_id} - processing immediately")
    elif priority == "medium":
        logger.info(f"Medium priority task {task_id} - processing in normal queue")
    else:
        logger.info(f"Low priority task {task_id} - processing when resources available")

    # Simulate potential errors (for testing)
    # In production, this would be actual business logic errors
    if task_data.get("title") == "__SIMULATE_TRANSIENT_ERROR__":
        raise TransientError("Simulated transient error - should retry")

    if task_data.get("title") == "__SIMULATE_PERMANENT_ERROR__":
        raise PermanentError("Simulated permanent error - should not retry")

    logger.info(f"Task {task_id} processed successfully")
