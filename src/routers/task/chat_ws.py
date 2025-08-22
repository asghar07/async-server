import json
import logging
import os
import traceback
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from langchain_core.messages import AIMessage, AIMessageChunk
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from src.agent import ChatAgentMetadata
from src.clients import get_async_client, get_firestore_client
from src.model.agent import AsyncConfig
from src.model.app.task import Message, MessageStatus, TaskStatus
from src.utils.chat_utils import handle_ai_message_chunk, parse_options_block, trim_options_block
from src.utils.message_utils import get_message_chunk_text, get_message_text
from src.utils.setup_utils import setup_repo_async
from src.utils.task_utils import summarize_task_async

END_OF_MESSAGE = "<end>"

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/chat")
async def chat_async(
    websocket: WebSocket,
    user_id: str,
    org_id: str,
    project_id: str,
    task_id: str,
    is_dev: bool = False,
):
    try:
        await websocket.accept()

        firestore_client = get_firestore_client()
        org = await firestore_client.get_org_async(org_id)
        project = await firestore_client.get_project_async(org_id, project_id)
        task = await firestore_client.get_task_async(org_id, task_id)
        repo_directory = await setup_repo_async(org, project)

        config = AsyncConfig(
            thread_id=task_id,
            repo_directory=repo_directory,
            org=org,
            project=project,
            task=task,
            user_id=user_id,
            is_dev=is_dev,
        )
        user_turns = 1

        while True:
            try:
                user_message = await websocket.receive_text()
                if user_message == "Execute":
                    await _handle_execute_task_async(config)

                config["user_message"] = user_message
                config["user_turns"] = user_turns
                await _run_agent_async(websocket, config)
                await _send_text_async(websocket)

                user_turns += 1
            except WebSocketDisconnect as e:
                raise e
            except RuntimeError as e:
                logger.error(f"Encountered error: {e}")
                break
            except Exception:
                traceback.print_exc()
                await _send_text_async(websocket)
    except WebSocketDisconnect as e:
        logger.debug(f"WebSocket disconnected: {e.code}")


async def _send_text_async(websocket: WebSocket, message: str = END_OF_MESSAGE):
    try:
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_text(message)
    except Exception:
        # ignore and let execution finishes
        pass


async def _run_agent_async(websocket: WebSocket, config: AsyncConfig):
    async with await AsyncConnection.connect(
        os.getenv("DB_URI"), autocommit=True, prepare_threshold=None, row_factory=dict_row
    ) as conn:
        async with conn.pipeline() as pipe:
            agent_metadata = ChatAgentMetadata(config)
            checkpointer = AsyncPostgresSaver(conn, pipe)
            agent = agent_metadata.create_agent(checkpointer)

            parent_message = await _create_streaming_message_async(
                config=config,
                author=agent.name,
                title=agent_metadata.get_default_title(),
            )

            partial_match = ""
            options_block = None

            firestore_client = get_firestore_client()

            try:
                async for mode, event in agent.astream(
                    input={"messages": agent_metadata.get_input_message()},
                    config={"configurable": config, "recursion_limit": 200},
                    stream_mode=["messages", "updates", "custom"],
                ):
                    if mode == "messages" and isinstance(event[0], AIMessageChunk):
                        content = get_message_chunk_text(event[0])
                        if not content:
                            continue

                        chunk, partial_match, options_block = handle_ai_message_chunk(
                            content, partial_match, options_block
                        )
                        if chunk:
                            await _send_text_async(websocket, chunk)
                    elif mode == "updates" and "agent" in event:
                        for message in event["agent"]["messages"]:
                            if not isinstance(message, AIMessage):
                                continue
                            parent_message.text = trim_options_block(get_message_text(message))
                    elif mode == "custom":
                        tool_message = f"<tool_call>{event.model_dump_json(exclude={'created_at'})}</tool_call>"
                        await _send_text_async(websocket, tool_message)

                message_actions = parse_options_block(options_block)
                if message_actions:
                    if any(message_action["label"] == "Execute" for message_action in message_actions):
                        config["task_summary"] = await summarize_task_async(parent_message.text)
                    await _send_text_async(websocket, f"<actions>{json.dumps(message_actions)}</actions>")

                await firestore_client.update_message_async(
                    config["org"].id,
                    config["task"].id,
                    message_id=parent_message.id,
                    status=MessageStatus.COMPLETED,
                    text=parent_message.text,
                    is_streaming=False,
                    actions=message_actions,
                )
            except Exception:
                await firestore_client.update_message_async(
                    config["org"].id,
                    config["task"].id,
                    message_id=parent_message.id,
                    status=MessageStatus.FAILED,
                    is_streaming=False,
                )
                raise


async def _create_streaming_message_async(config: AsyncConfig, author: str, title: str) -> Message:
    message = Message(
        author=author,
        title=title,
        text="",
        status=MessageStatus.IN_PROGRESS,
        is_streaming=True,
    )
    return await get_firestore_client().create_message_async(config["org"].id, config["task"].id, message)


async def _handle_execute_task_async(config: AsyncConfig):
    await get_firestore_client().update_task_async(
        config["org"].id,
        config["task"].id,
        overview=config["task_summary"].overview,
        requirements=config["task_summary"].requirements,
        status=TaskStatus.EXECUTING,
        last_updated=datetime.now(timezone.utc),
    )
    await get_async_client().invoke_execute_task_job_async(config["org"].id, config["task"].id, config["is_dev"])
