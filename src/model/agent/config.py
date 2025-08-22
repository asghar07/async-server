from typing_extensions import TypedDict

from src.model.agent.response import TaskSummary
from src.model.app import Org
from src.model.app.project import Project
from src.model.app.task import Task


class AsyncConfig(TypedDict, total=False):
    """
    Class containing immutable configuration that contains session information
    """

    thread_id: str
    """
    Unique ID assigned to each checkpoint saved by a checkpointer LangGraph concept
    """

    repo_directory: str
    """
    Absolute path to the cloned repository
    """

    org: Org
    """
    Organization model
    """

    project: Project
    """
    Project model
    """

    task: Task
    """
    Task model
    """

    user_id: str
    """
    User ID
    """

    user_message: str
    """
    User message
    """

    user_turns: int
    """
    Number of messages the user has sent
    """

    is_dev: bool
    """
    Boolean to tell whether the request is for development
    """

    task_summary: TaskSummary
    """
    Summary of the task
    """
