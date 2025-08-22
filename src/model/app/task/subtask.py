from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from src.model import generate_id
from src.model.app.task.diff import DiffComment, DiffFile


class SubtaskStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "inProgress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Subtask(BaseModel):
    id: str = Field(default_factory=generate_id)
    order: int
    title: str
    steps: list[str]

    diff_comments: list[DiffComment] = []
    diff_files: list[DiffFile] = []
    pull_request_commit: str = ""

    status: SubtaskStatus = SubtaskStatus.CREATED
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_description(self) -> str:
        if not self.steps:
            return ""

        formatted_steps = []
        for i, step in enumerate(self.steps, 1):
            formatted_steps.append(f"{i}. {step.strip()}")
        return "\n".join(formatted_steps)
