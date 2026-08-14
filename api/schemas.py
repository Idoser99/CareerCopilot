from datetime import datetime
from typing import Any, Literal
from uuid import UUID

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


class AgentSessionMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentSessionSummaryResponse(BaseModel):
    id: UUID
    title: str


class AgentSessionResponse(AgentSessionSummaryResponse):
    messages: list[AgentSessionMessage]


class ProfileSummaryResponse(BaseModel):
    id: UUID
    name: str
    email: str
    has_cv: bool


class ProfileResponse(BaseModel):
    id: UUID
    name: str
    email: str
    cv_text: str | None
    created_at: datetime


class CvUploadRequest(BaseModel):
    cv_text: str


class ApplicationResponse(BaseModel):
    id: UUID
    profile_id: UUID
    job_id: str
    job_title: str
    company: str
    tailored_cv_text: str | None
    status: Literal[
        "draft", "pending", "accepted", "rejected", "withdrawn", "scheduled"
    ]
    submitted_at: datetime | None
    created_at: datetime


class EmailResponse(BaseModel):
    id: UUID
    application_id: UUID
    direction: Literal["inbound", "outbound"]
    type: Literal["submitted", "accepted", "rejected", "confirmation"]
    subject: str
    body: str
    created_at: datetime


class CalendarEventResponse(BaseModel):
    id: UUID
    application_id: UUID
    event_type: Literal["interview", "preparation"]
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    status: Literal["scheduled", "cancelled", "completed"]
