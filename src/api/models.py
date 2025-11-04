"""Pydantic models for task validation."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskCreateRequest(BaseModel):
    """Request model for creating a new task."""

    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(..., min_length=1, max_length=2000, description="Task description")
    priority: TaskPriority = Field(..., description="Task priority level")
    due_date: Optional[str] = Field(None, description="ISO 8601 timestamp for due date")

    @field_validator("title", "description")
    @classmethod
    def sanitize_string(cls, v: str) -> str:
        """Sanitize string fields by stripping whitespace."""
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("Field cannot be empty after stripping whitespace")
            return stripped
        return v

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate and parse ISO 8601 date string."""
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        try:
            # Parse ISO 8601 format
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 date format: {v}") from e

        return v


class TaskResponse(BaseModel):
    """Response model for created task."""

    task_id: str = Field(..., description="Unique task identifier")
    message: str = Field(default="Task created successfully", description="Response message")
