from pydantic import BaseModel, Field


class TaskSummary(BaseModel):
    overview: str = Field(description="A one paragraph overview of the task")
    requirements: list[str] = Field(description="List of requirements for the task")
