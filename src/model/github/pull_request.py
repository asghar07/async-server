from pydantic import BaseModel

from src.model.github.account import Account


class PullRequestCommit(BaseModel):
    ref: str
    sha: str


class PullRequest(BaseModel):
    id: int
    url: str
    html_url: str
    title: str
    body: str
    user: Account
    head: PullRequestCommit
    base: PullRequestCommit
    merged: bool


class PullRequestFile(BaseModel):
    filename: str
