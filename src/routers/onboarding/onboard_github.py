from fastapi import APIRouter, BackgroundTasks, status

from src.api.onboarding import OnboardingGithubRequest, OnboardingGithubResponse
from src.clients import get_async_client, get_firestore_client, get_github_client, get_secret_client
from src.model.app import Org, OrgType, Profile, User, UserRole
from src.model.app.project import Project
from src.model.app.project import Repository as AsyncRepository
from src.model.app.task import Task, TaskComment, TaskSource
from src.model.github import Installation, Repository

router = APIRouter()


@router.post("/onboard-github", status_code=status.HTTP_200_OK)
async def onboard_github_async(
    request: OnboardingGithubRequest, background_tasks: BackgroundTasks
) -> OnboardingGithubResponse:
    firestore_client = get_firestore_client()
    github_client = get_github_client()
    secret_client = get_secret_client()

    installation = await github_client.get_installation_async(request.installation_id)
    org = await _create_org_async(installation)
    user = await firestore_client.update_user_async(request.user_id, org_id=org.id, role=UserRole.ADMIN)
    await _create_user_profile_async(user, org.id)

    client_id = await secret_client.get_async_github_app_client_id_async()
    client_secret = await secret_client.get_async_github_app_client_secret_async()
    user_access_token = await github_client.get_access_token_async(client_id, client_secret, request.code)
    await secret_client.create_user_github_token_secret_async(request.user_id, user_access_token)

    github_id, github_login = await github_client.get_user_information_async(user_access_token)
    await firestore_client.update_user_async(request.user_id, github_id=github_id, github_login=github_login)

    access_token = await github_client.generate_app_access_token_async(request.installation_id)
    async for repo in github_client.list_installation_repos_async(access_token):
        project = await _create_project_async(org.id, repo)
        await _create_repository_async(org.id, project)
        await get_async_client().invoke_index_project_job_async(org.id, project.id, request.is_dev)
        background_tasks.add_task(_process_repository_issues_async, access_token, user.id, org.id, project)
    await firestore_client.update_org_async(org.id, onboarded=True)
    return OnboardingGithubResponse()


async def _create_org_async(installation: Installation) -> Org:
    account = installation.account
    github_account_type = OrgType.USER if account.type == "User" else OrgType.ORGANIZATION

    org = Org(
        name=account.login,
        github_installation_id=installation.id,
        github_account_type=github_account_type,
        github_account_name=account.login,
        github_avatar_url=account.avatar_url,
        onboarded=False,
    )
    return await get_firestore_client().create_org_async(org)


async def _create_user_profile_async(user: User, org_id: str):
    profile = Profile(
        id=user.id,
        name=user.name,
        email=user.email,
    )
    await get_firestore_client().create_profile_async(org_id, profile)


async def _create_project_async(org_id: str, repo: Repository) -> Project:
    project = Project(
        name=repo.name,
        repo=repo.full_name,
        description=repo.description or "",
    )
    return await get_firestore_client().create_project_async(org_id, project)


async def _create_repository_async(org_id: str, project: Project):
    repository = AsyncRepository(
        full_name=project.repo,
        org_id=org_id,
        project_id=project.id,
    )
    await get_firestore_client().create_repository_async(repository)


async def _process_repository_issues_async(access_token: str, user_id: str, org_id: str, project: Project):
    firestore_client = get_firestore_client()
    task_ids = []
    async for github_issue in get_github_client().list_repository_open_issues_async(access_token, project.repo):
        task_comments = []
        async for github_issue_comment in get_github_client().list_issue_comments_async(
            access_token, project.repo, github_issue.number
        ):
            task_comments.append(
                TaskComment(
                    author=github_issue_comment.user.login,
                    body=github_issue_comment.body,
                    created_at=github_issue_comment.created_at,
                )
            )
        task = Task(
            title=github_issue.title,
            body=github_issue.body,
            author=github_issue.user.login,
            source=TaskSource.GITHUB,
            comments=task_comments,
            github_issue_id=github_issue.id,
            github_issue_number=github_issue.number,
            project_id=project.id,
            created_at=github_issue.created_at,
        )
        await firestore_client.create_task_async(org_id, task)

        # Auto subsribe all ingested tasks to the user who created the org.
        # Update user doc for each task so the UI can dynamically show the update.
        task_ids.append(task.id)
        await firestore_client.update_user_async(user_id, subscribed_tasks=task_ids)
