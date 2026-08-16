import os
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, Response
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from data.db import database as db
from api.agent_metadata import create_agent_info
from api.schemas import (
    AgentInfoResponse,
    AgentSessionResponse,
    AgentSessionSummaryResponse,
    ApplicationResponse,
    CalendarEventResponse,
    CvUploadRequest,
    DemoApplicationDecisionRequest,
    DemoApplicationDecisionResponse,
    EmailResponse,
    ExecuteRequest,
    ExecuteResponse,
    NotificationResponse,
    ProfileResponse,
    ProfileSummaryResponse,
    Student,
    TeamInfoResponse,
)
from agent.registry import create_registry
from agent.agent import Agent
from agent.agent_session import AgentSession
from services.cv_document import (
    CVWriteError,
    create_application_cv_docx,
    create_profile_cv_docx,
)
from services.demo_application_decision import demo_application_decision_service

load_dotenv()

default_profile_id = os.getenv("DEFAULT_PROFILE_ID", "").strip()
PROFILE_HEADER = Header(alias="X-Profile-Id")
SESSION_HEADER_NAME = "X-Session-Id"
SESSION_HEADER = Header(alias=SESSION_HEADER_NAME)
TRACK_SESSION_HEADER = Header(alias="X-Track-Session")

model_name = os.getenv("OPENAI_MODEL_PREFIX") + "-" + "gpt-5-mini"
llm = ChatOpenAI(model=model_name)

app = FastAPI()


@app.get("/ping")
def ping():
    return "pong"


@app.get("/api/team_info", response_model=TeamInfoResponse)
def team_info() -> TeamInfoResponse:
    return TeamInfoResponse(
        group_batch_order_number="1_5",
        team_name="Ido & Yarden - CareerCopilot",
        students=[
            Student(name="Ido Oserovitz", email="idoser99@gmail.com"),
            Student(name="Yarden Basharim", email="basharimyar@gmail.com"),
        ],
    )


@app.get("/api/agent_info", response_model=AgentInfoResponse)
def agent_info() -> AgentInfoResponse:
    return create_agent_info()


@app.get("/api/model_architecture", response_class=FileResponse)
def agent_architecture():
    return FileResponse("resources/architecture.png", media_type="image/png")


@app.post("/api/execute", response_model=ExecuteResponse)
def execute(
        request: ExecuteRequest,
        response: Response,
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
        header_session_id: Annotated[str | None, SESSION_HEADER] = None,
        track_session: Annotated[bool, TRACK_SESSION_HEADER] = False,
) -> ExecuteResponse:
    try:
        profile_id = get_profile_id(header_profile_id)
        session = None
        session_id = None
        session_title = None

        if header_session_id:
            session_id = get_session_id(header_session_id)
            stored_session = db.get_agent_session(profile_id, session_id)
            stored_messages = stored_session.get("messages") or []
            session = AgentSession(history=stored_messages)
            session_title = stored_session.get("title") or "New conversation"
            if not stored_messages and session_title == "New conversation":
                session_title = create_session_title(request.prompt)
        elif track_session:
            session_title = create_session_title(request.prompt)
            stored_session = db.create_agent_session(
                profile_id=profile_id,
                messages=[],
                title=session_title,
            )
            session_id = UUID(stored_session["id"])
            session = AgentSession()

        if session_id:
            response.headers[SESSION_HEADER_NAME] = str(session_id)

        registry = create_registry(profile_id)
        career_copilot = Agent(llm, registry)
        agent_response = career_copilot.invoke(
            prompt=request.prompt,
            session=session
        )

        if track_session and session_id:
            db.update_agent_session(
                profile_id=profile_id,
                session_id=session_id,
                messages=session.get_lean_session(),
                title=session_title,
            )
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

@app.post("/api/sessions", response_model=AgentSessionSummaryResponse)
def create_agent_session(
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> AgentSessionSummaryResponse:
    profile_id = get_profile_id(header_profile_id)
    session = db.create_agent_session(profile_id, [])
    return AgentSessionSummaryResponse(
        id=session["id"],
        title=session.get("title") or "New conversation",
    )


@app.get("/api/sessions", response_model=list[AgentSessionSummaryResponse])
def get_agent_sessions(
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> list[AgentSessionSummaryResponse]:
    profile_id = get_profile_id(header_profile_id)
    return [
        AgentSessionSummaryResponse(
            id=session["id"],
            title=session.get("title") or "New conversation",
        )
        for session in db.get_agent_sessions(profile_id)
    ]


@app.get("/api/sessions/{session_id}", response_model=AgentSessionResponse)
def get_agent_session(
        session_id: UUID,
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> AgentSessionResponse:
    profile_id = get_profile_id(header_profile_id)
    session = db.get_agent_session(profile_id, session_id)
    return AgentSessionResponse(
        id=session["id"],
        title=session.get("title") or "New conversation",
        messages=session.get("messages") or [],
    )

@app.get("/api/profiles", response_model=list[ProfileSummaryResponse])
def get_profiles() -> list[ProfileSummaryResponse]:
    profiles = db.get_profiles()
    return [
        ProfileSummaryResponse(
            id=profile["id"],
            name=profile["name"],
            email=profile["email"],
            has_cv=bool((profile.get("cv_text") or "").strip()),
            is_default=str(profile["id"]) == default_profile_id,
        )
        for profile in profiles
    ]


@app.get("/api/profile", response_model=ProfileResponse)
def get_profile(
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> ProfileResponse:
    profile_id = get_profile_id(header_profile_id)
    return ProfileResponse(**db.get_profile(profile_id))


@app.get("/api/notifications", response_model=list[NotificationResponse])
def get_notifications(
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> list[NotificationResponse]:
    profile_id = get_profile_id(header_profile_id)
    return db.list_notifications(profile_id)


@app.patch("/api/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
        notification_id: UUID,
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> NotificationResponse:
    profile_id = get_profile_id(header_profile_id)
    return db.mark_notification_as_read(profile_id, notification_id)


@app.patch("/api/notifications/read-all", response_model=list[NotificationResponse])
def mark_all_notifications_as_read(
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> list[NotificationResponse]:
    profile_id = get_profile_id(header_profile_id)
    return db.mark_all_notifications_as_read(profile_id)


@app.post("/api/demo/applications/{application_id}/decision", response_model=DemoApplicationDecisionResponse)
def simulate_application_decision(
        application_id: UUID,
        request: DemoApplicationDecisionRequest,
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None
) -> DemoApplicationDecisionResponse:
    profile_id = get_profile_id(header_profile_id)
    email, notification = demo_application_decision_service.simulate(
        profile_id=profile_id,
        application_id=application_id,
        decision=request.decision,
    )
    return DemoApplicationDecisionResponse(
        decision=request.decision,
        email=email,
        notification=notification,
    )


@app.get("/api/applications", response_model=list[ApplicationResponse])
def get_applications(
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None
) -> list[ApplicationResponse]:
    profile_id = get_profile_id(header_profile_id)
    return db.get_applications(profile_id)


@app.get("/api/applications/{application_id}/cv/download")
def download_application_cv(
        application_id: UUID,
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> Response:
    profile_id = get_profile_id(header_profile_id)
    profile = db.get_profile(profile_id)
    application = db.get_application(profile_id, application_id)
    try:
        document, filename = create_application_cv_docx(profile, application)
    except CVWriteError as error:
        raise HTTPException(404, error.message) from error

    return Response(
        content=document.getvalue(),
        media_type=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        headers={"Content-Disposition": (f"attachment; filename*=UTF-8''{quote(filename)}")}
    )


@app.get("/api/emails", response_model=list[EmailResponse])
def get_emails(
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> list[EmailResponse]:
    profile_id = get_profile_id(header_profile_id)
    return db.get_emails(profile_id)


@app.get("/api/calendar", response_model=list[CalendarEventResponse])
def get_calendar_events(
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> list[CalendarEventResponse]:
    profile_id = get_profile_id(header_profile_id)
    return db.get_calendar_events(profile_id)


@app.post("/api/profile/cv", response_model=ProfileResponse)
def upload_cv(
        request: CvUploadRequest,
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> ProfileResponse:
    profile_id = get_profile_id(header_profile_id)
    return ProfileResponse(**db.set_profile_cv(profile_id, request.cv_text))


@app.get("/api/profile/cv/download")
def download_cv(
        header_profile_id: Annotated[str | None, PROFILE_HEADER] = None,
) -> Response:
    profile_id = get_profile_id(header_profile_id)
    profile = db.get_profile(profile_id)
    try:
        document, filename = create_profile_cv_docx(profile)
    except CVWriteError as error:
        raise HTTPException(404, error.message) from error

    return Response(
        content=document.getvalue(),
        media_type=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        headers={"Content-Disposition": (f"attachment; filename*=UTF-8''{quote(filename)}")}
    )


def get_profile_id(header_profile_id: str | None) -> UUID:
    profile_id = header_profile_id or default_profile_id
    try:
        return UUID(profile_id)
    except ValueError as error:
        raise HTTPException(400, "Profile ID must be a valid UUID") from error


def get_session_id(header_session_id: str) -> UUID:
    try:
        return UUID(header_session_id)
    except ValueError as error:
        raise HTTPException(400, "Session ID must be a valid UUID") from error


def create_session_title(prompt: str) -> str:
    title = " ".join(prompt.split())
    if not title:
        return "New conversation"
    return title[:57] + "..." if len(title) > 60 else title
