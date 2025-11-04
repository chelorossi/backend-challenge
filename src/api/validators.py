"""Validation and sanitization utilities."""

import json
from typing import Any, Dict

from pydantic import ValidationError

from .models import TaskCreateRequest


def validate_task_request(body: str) -> tuple[TaskCreateRequest | None, str | None, int]:
    """
    Validate and sanitize task creation request.

    Args:
        body: JSON string of the request body

    Returns:
        Tuple of (validated_task, error_message, status_code)
        If validation succeeds: (TaskCreateRequest, None, 200)
        If validation fails: (None, error_message, 400)
    """
    if not body:
        return None, "Request body is required", 400

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {str(e)}", 400

    try:
        task = TaskCreateRequest(**data)
        return task, None, 200
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"{field}: {message}")
        return None, "; ".join(error_messages), 400
