from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

from api.db import database as db
from api.schemas import (
    AgentInfoResponse,
    ApplicationResponse,
    CalendarEventResponse,
    EmailResponse,
    ExecuteRequest,
    ExecuteResponse,
    ExecutionStep,
    ProfileResponse,
    ProfileSummaryResponse,
    PromptExample,
    PromptTemplate,
    Student,
    TeamInfoResponse,
)
from agent.registry import create_registry
from agent.agent import Agent

load_dotenv()

default_profile_id = os.getenv("DEFAULT_PROFILE_ID", "").strip()
PROFILE_HEADER = Header(alias="X-Profile-Id")

model_name = os.getenv("OPENAI_MODEL_PREFIX") + "-" + "gpt-5-mini"
llm = ChatOpenAI(model=model_name)

app = FastAPI()

@app.get("/ping")
def ping():
    return "pong"


@app.get("/api/team_info", response_model=TeamInfoResponse)
def team_info() -> TeamInfoResponse:
    return TeamInfoResponse(
        group_batch_order_number="1_{order#}",
        team_name="Ido & Yarden",
        students=[
            Student(name="Ido Oserovitz", email="idoser99@gmail.com"),
            Student(name="Yarden", email="yarden@gmail.com"),
        ],
    )


@app.get("/api/agent_info", response_model=AgentInfoResponse)
def agent_info() -> AgentInfoResponse:
    return AgentInfoResponse(
        description="…",
        purpose="…",
        prompt_template=PromptTemplate(template="…"),
        prompt_examples=[
            PromptExample(
                prompt="Example prompt 1…",
                full_response="Full response your agent returns…",
                steps=[
                    ExecutionStep(
                        module="CV Tailoring",
                        prompt={},
                        response={},
                    )
                ],
            ),
            PromptExample(
                prompt="Example prompt 2…",
                full_response="Full response your agent returns…",
                steps=[
                    ExecutionStep(
                        module="Submit Application",
                        prompt={},
                        response={},
                    )
                ],
            ),
        ],
    )


@app.get("/api/model_architecture", response_class=FileResponse)
def agent_architecture():
    return FileResponse("resources/architecture.png", media_type="image/png")


@app.post("/api/execute", response_model=ExecuteResponse)
def execute(
    request: ExecuteRequest,
    header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> ExecuteResponse:
    # todo: add augmented prompt for career copilot
    try:
        profile_id = get_profile_id(header_profile_id)
        registry = create_registry(profile_id)
        career_copilot = Agent(llm, registry)
        agent_response = career_copilot.invoke(prompt=request.prompt)
        return ExecuteResponse(
            status="ok",
            error=None,
            response=agent_response.content,
            steps=agent_response.steps
        )
    except Exception as e:
        return ExecuteResponse(
            status="error",
            error=str(e),
            response=None,
            steps=[]
        )


# -------------- client services ---------------

@app.get("/api/profiles", response_model=list[ProfileSummaryResponse])
def get_profiles() -> list[ProfileSummaryResponse]:
    profiles = db.get_profiles()
    return [
        ProfileSummaryResponse(
            id=profile["id"],
            name=profile["name"],
            email=profile["email"],
            has_cv=bool((profile.get("cv_text") or "").strip()),
        )
        for profile in profiles
    ]


@app.get("/api/profile", response_model=ProfileResponse)
def get_profile(
    header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> ProfileResponse:
    profile_id = get_profile_id(header_profile_id)
    return ProfileResponse(**db.get_profile(profile_id))


@app.get("/api/applications", response_model=list[ApplicationResponse])
def get_applications(
    header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> list[ApplicationResponse]:
    profile_id = get_profile_id(header_profile_id)
    return db.get_applications(profile_id)


@app.get("/api/emails", response_model=list[EmailResponse])
def get_emails(
    header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> list[EmailResponse]:
    profile_id = get_profile_id(header_profile_id)
    return db.get_emails(profile_id)


@app.get("/api/calendar", response_model=list[CalendarEventResponse])
@app.get(
    "/api/calander",
    response_model=list[CalendarEventResponse],
    include_in_schema=False,
)
def get_calendar_events(
    header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> list[CalendarEventResponse]:
    profile_id = get_profile_id(header_profile_id)
    return db.get_calendar_events(profile_id)


def get_profile_id(header_profile_id: str | None) -> UUID:
    profile_id = header_profile_id or default_profile_id
    try:
        return UUID(profile_id)
    except ValueError as error:
        raise HTTPException(400, "Profile ID must be a valid UUID") from error
