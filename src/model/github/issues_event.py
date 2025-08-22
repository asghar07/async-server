from enum import Enum

from pydantic import BaseModel

from src.model.github.issue import Issue
from src.model.github.repository import Repository


class IssuesEventAction(str, Enum):
    OPENED = "opened"
    EDITED = "edited"
    CLOSED = "closed"
    REOPENED = "reopened"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"


class IssuesEvent(BaseModel):
    action: IssuesEventAction
    issue: Issue
    repository: Repository
