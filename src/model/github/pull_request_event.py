from enum import Enum

from pydantic import BaseModel

from src.model.github.account import Account
from src.model.github.organization import Organization
from src.model.github.pull_request import PullRequest
from src.model.github.repository import Repository


class PullRequestEventAction(str, Enum):
    OPENED = "opened"
    CLOSED = "closed"
    SYNCHRONIZE = "synchronize"


class PullRequestEventInstallation(BaseModel):
    id: int


class PullRequestEvent(BaseModel):
    action: PullRequestEventAction
    number: int
    sender: Account
    organization: Organization
    pull_request: PullRequest
    repository: Repository
    installation: PullRequestEventInstallation
