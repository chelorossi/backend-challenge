"""Unit tests for validation logic."""

import json
import pytest

from src.api.models import TaskCreateRequest, TaskPriority
from src.api.validators import validate_task_request


def test_validate_task_request_valid():
    """Test validation of valid task request."""
    body = json.dumps(
        {
            "title": "Test Task",
            "description": "Test Description",
            "priority": "high",
            "due_date": "2024-12-31T23:59:59Z",
        }
    )

    task, error, status = validate_task_request(body)

    assert task is not None
    assert error is None
    assert status == 200
    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.priority == TaskPriority.HIGH
    assert task.due_date == "2024-12-31T23:59:59Z"


def test_validate_task_request_no_due_date():
    """Test validation of task request without due date."""
    body = json.dumps(
        {"title": "Test Task", "description": "Test Description", "priority": "medium"}
    )

    task, error, status = validate_task_request(body)

    assert task is not None
    assert error is None
    assert status == 200
    assert task.due_date is None


def test_validate_task_request_empty_body():
    """Test validation with empty body."""
    task, error, status = validate_task_request("")

    assert task is None
    assert error is not None
    assert "required" in error.lower()
    assert status == 400


def test_validate_task_request_invalid_json():
    """Test validation with invalid JSON."""
    task, error, status = validate_task_request("{ invalid json }")

    assert task is None
    assert error is not None
    assert "invalid json" in error.lower()
    assert status == 400


def test_validate_task_request_missing_fields():
    """Test validation with missing required fields."""
    body = json.dumps(
        {
            "title": "Test Task"
            # Missing description and priority
        }
    )

    task, error, status = validate_task_request(body)

    assert task is None
    assert error is not None
    assert status == 400


def test_validate_task_request_invalid_priority():
    """Test validation with invalid priority."""
    body = json.dumps(
        {"title": "Test Task", "description": "Test Description", "priority": "invalid"}
    )

    task, error, status = validate_task_request(body)

    assert task is None
    assert error is not None
    assert status == 400


def test_validate_task_request_invalid_due_date():
    """Test validation with invalid due date format."""
    body = json.dumps(
        {
            "title": "Test Task",
            "description": "Test Description",
            "priority": "low",
            "due_date": "not-a-date",
        }
    )

    task, error, status = validate_task_request(body)

    assert task is None
    assert error is not None
    assert "invalid" in error.lower()
    assert status == 400


def test_validate_task_request_whitespace_sanitization():
    """Test that whitespace is sanitized from title and description."""
    body = json.dumps(
        {"title": "  Test Task  ", "description": "  Test Description  ", "priority": "high"}
    )

    task, error, status = validate_task_request(body)

    assert task is not None
    assert task.title == "Test Task"
    assert task.description == "Test Description"


def test_validate_task_request_empty_string_after_strip():
    """Test validation with empty string after stripping."""
    body = json.dumps({"title": "   ", "description": "Test Description", "priority": "high"})

    task, error, status = validate_task_request(body)

    assert task is None
    assert error is not None
    assert status == 400


def test_validate_task_request_all_priorities():
    """Test validation with all priority levels."""
    for priority in ["low", "medium", "high"]:
        body = json.dumps(
            {"title": "Test Task", "description": "Test Description", "priority": priority}
        )

        task, error, status = validate_task_request(body)

        assert task is not None
        assert error is None
        assert status == 200
        assert task.priority.value == priority
