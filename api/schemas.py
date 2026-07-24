from typing import Any
from pydantic import BaseModel


class Student(BaseModel):
    name: str
    email: str


class TeamInfoResponse(BaseModel):
    group_batch_order_number: str
    team_name: str
    students: list[Student]


class ExecutionStep(BaseModel):
    module: str
    prompt: dict[str, Any]
    response: dict[str, Any]


class PromptTemplate(BaseModel):
    template: str


class PromptExample(BaseModel):
    prompt: str
    full_response: str
    steps: list[ExecutionStep]


class AgentInfoResponse(BaseModel):
    description: str
    purpose: str
    prompt_template: PromptTemplate
    prompt_examples: list[PromptExample]


class ExecuteRequest(BaseModel):
    prompt: str


class ExecuteResponse(BaseModel):
    status: str
    error: str | None
    response: str | None
    steps: list[ExecutionStep]
