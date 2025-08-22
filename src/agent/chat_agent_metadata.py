from typing import Callable, Optional, Sequence, Union

from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt.chat_agent_executor import StructuredResponseSchema
from langgraph.prebuilt.tool_node import ToolNode

from src.agent.agent_metadata import AgentMetadata
from src.prompt.chat_prompt import CHAT_PROMPT
from src.tools.filesystem import ListFiles, ReadFile
from src.tools.git import GitGrep


class ChatAgentMetadata(AgentMetadata):
    """
    Chat agent parameters
    """

    def get_default_title(self) -> str:
        return "Gathering requirements"

    def get_input_message(self) -> str:
        return (
            f"- user inquiry: {self.config['user_message']}\n"
            f"- project overview: {self.config['project'].overview}\n"
            f"- project file structure: {self.config['project'].tree}\n"
            f"- repo directory: {self.config['repo_directory']}\n"
            f"This is your {self.config['user_turns']}th turn"
        )

    def _get_name(self) -> str:
        return "chat-agent"

    def _get_model(self) -> LanguageModelLike:
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    def _get_system_prompt(self) -> str:
        return CHAT_PROMPT

    def _get_tools(self) -> Union[Sequence[Union[BaseTool, Callable]], ToolNode]:
        return [ListFiles(), ReadFile(), GitGrep()]

    def _get_response_format(self) -> Optional[StructuredResponseSchema]:
        return None
