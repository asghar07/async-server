from src.clients import get_firestore_client
from src.model import compute_repository_doc_id
from src.model.app import User
from src.model.app.task import Task, TaskSource
from src.model.github import Issue, IssuesEvent, IssuesEventAction


async def handle_issues_async(event: IssuesEvent):
    match event.action:
        case IssuesEventAction.OPENED:
            await _handle_issue_opened_async(event)
        case _:
            pass


async def _handle_issue_opened_async(event: IssuesEvent):
    firestore_client = get_firestore_client()
    repository = await firestore_client.get_repository_async(compute_repository_doc_id(event.repository.full_name))

    task = Task(
        title=event.issue.title,
        body=event.issue.body,
        author=event.issue.user.login,
        source=TaskSource.GITHUB,
        comments=[],
        github_issue_id=event.issue.id,
        github_issue_number=event.issue.number,
        project_id=repository.project_id,
        created_at=event.issue.created_at,
    )
    await firestore_client.create_task_async(repository.org_id, task)

    users = await firestore_client.get_users_in_org_async(repository.org_id)
    for user in users:
        # for now, only subsribe the task if either it's created by the user or it's assigned to the user
        if not _is_created_by_user(user, event.issue) and not _is_assigned_to_user(user, event.issue):
            continue

        user.subscribed_tasks.append(task.id)
        await firestore_client.update_user_async(user.id, subscribed_tasks=user.subscribed_tasks)


def _is_created_by_user(user: User, issue: Issue) -> bool:
    return user.github_id == issue.user.id


def _is_assigned_to_user(user: User, issue: Issue) -> bool:
    return issue.assignee and user.github_id == issue.assignee.id
