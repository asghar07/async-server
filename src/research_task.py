import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime, timezone

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.agent import ResearchAgentMetadata, SummaryAgentMetadata
from src.clients import get_firestore_client
from src.execute_task import execute_task_async
from src.model.agent import AsyncConfig
from src.model.agent.response import TaskResearchOutput, TaskSummary
from src.model.app.task import TaskQuestion, TaskStatus
from src.utils.bootstrap_utils import bootstrap_application_async, create_bootstrap_config
from src.utils.filesystem_utils import cleanup_directory_async
from src.utils.setup_utils import setup_ephemeral_repo_async

logger = logging.getLogger(__name__)


async def research_task_async(org_id: str, task_id: str, is_dev: bool):
    task_directory = None
    try:
        firestore_client = get_firestore_client()
        await firestore_client.update_task_async(
            org_id, task_id, status=TaskStatus.RESEARCHING, last_updated=datetime.now(timezone.utc)
        )

        org = await firestore_client.get_org_async(org_id)
        task = await firestore_client.get_task_async(org_id, task_id)
        project = await firestore_client.get_project_async(org_id, task.project_id)
        task_directory, repo_directory = await setup_ephemeral_repo_async(org.github_installation_id, project.repo)

        config = AsyncConfig(
            thread_id=task.id,
            repo_directory=repo_directory,
            org=org,
            project=project,
            task=task,
            is_dev=is_dev,
        )
        research_output = await _research_async(config)
        task_summary = await _summarize_async(config)
        await _update_task_async(config, research_output, task_summary)

        if not research_output.clarifying_questions and org.credits > 0:
            logger.info(f"Task is ready to execute: {task_id}")
            await firestore_client.update_task_async(org_id, task_id, status=TaskStatus.EXECUTING)
            await execute_task_async(config["org"].id, config["task"].id, config["is_dev"])

        logger.info(f"Finished researching task: {task_id}")
    except Exception:
        traceback.print_exc()
        await firestore_client.update_task_async(
            org_id, task_id, status=TaskStatus.FAILED, last_updated=datetime.now(timezone.utc)
        )
        sys.exit(1)
    finally:
        await cleanup_directory_async(task_directory)


async def _research_async(config: AsyncConfig) -> TaskResearchOutput:
    async with await AsyncConnection.connect(
        os.getenv("DB_URI"), autocommit=True, prepare_threshold=None, row_factory=dict_row
    ) as conn:
        async with conn.pipeline() as pipe:
            agent_metadata = ResearchAgentMetadata(config)
            checkpointer = AsyncPostgresSaver(conn, pipe)
            agent = agent_metadata.create_agent(checkpointer)
            response = await agent.ainvoke(
                input={"messages": agent_metadata.get_input_message()},
                config={"configurable": config, "recursion_limit": 500},
            )
            return response["structured_response"]


async def _summarize_async(config: AsyncConfig) -> TaskSummary:
    async with await AsyncConnection.connect(
        os.getenv("DB_URI"), autocommit=True, prepare_threshold=None, row_factory=dict_row
    ) as conn:
        async with conn.pipeline() as pipe:
            agent_metadata = SummaryAgentMetadata(config)
            checkpointer = AsyncPostgresSaver(conn, pipe)
            agent = agent_metadata.create_agent(checkpointer)
            response = await agent.ainvoke(
                input={"messages": agent_metadata.get_input_message()},
                config={"configurable": config, "recursion_limit": 5},
            )
            return response["structured_response"]


async def _update_task_async(config: AsyncConfig, research_output: TaskResearchOutput, task_summary: TaskSummary):
    firestore_client = get_firestore_client()
    questions = [
        TaskQuestion(
            question=q.question,
            options=[o.label for o in q.options],
            requirements=[o.requirement for o in q.options],
        )
        for q in research_output.clarifying_questions
    ]
    await firestore_client.update_task_async(
        org_id=config["org"].id,
        task_id=config["task"].id,
        overview=task_summary.overview,
        requirements=task_summary.requirements,
        status=TaskStatus.PENDING_FEEDBACK if research_output.clarifying_questions else TaskStatus.READY,
        questions=[question.model_dump() for question in questions],
        last_updated=datetime.now(timezone.utc),
    )


async def main(org_id: str, task_id: str, is_dev: bool):
    await bootstrap_application_async(create_bootstrap_config(is_dev))

    logger.info("Starting research_task job with params:")
    logger.info(f"  org_id={org_id}")
    logger.info(f"  task_id={task_id}")
    logger.info(f"  is_dev={is_dev}")

    await research_task_async(org_id, task_id, is_dev)


if __name__ == "__main__":
    asyncio.run(
        main(
            org_id=os.getenv("ORG_ID"),
            task_id=os.getenv("TASK_ID"),
            is_dev=os.getenv("IS_DEV", "False") == "True",
        )
    )
