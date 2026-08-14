import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import HTTPException
from supabase import Client, create_client

from data.jobs_db import JobsDatabase


load_dotenv()

APPLICATION_STATUSES = {
    "draft", "pending", "accepted", "rejected", "withdrawn", "scheduled"
}
CALENDAR_EVENT_TYPES = {"interview", "preparation"}
CALENDAR_EVENT_STATUSES = {"scheduled", "cancelled", "completed"}


def _execute(query) -> list[dict]:
    try:
        return query.execute().data or []
    except Exception as error:
        raise HTTPException(502, "Database request failed") from error


class Database:
    def __init__(self):
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
        self._client = create_client(url, key) if url and key else None
        self._jobs = JobsDatabase()

    def _get_client(self) -> Client:
        if self._client is None:
            raise HTTPException(503, "Supabase is not configured on the server")
        return self._client

    def get_profiles(self) -> list[dict]:
        return _execute(
            self._get_client()
            .table("profiles")
            .select("id,name,email,cv_text")
            .order("name")
        )

    def get_profile(self, profile_id: UUID) -> dict:
        profiles = _execute(
            self._get_client()
            .table("profiles")
            .select("id,name,email,cv_text,created_at")
            .eq("id", str(profile_id))
            .limit(1)
        )
        if not profiles:
            raise HTTPException(404, "Profile not found")
        return profiles[0]

    def set_profile_cv(self, profile_id: UUID, cv_text: str) -> dict:
        profiles = _execute(
            self._get_client()
            .table("profiles")
            .update({"cv_text": cv_text})
            .eq("id", str(profile_id))
        )
        if not profiles:
            raise HTTPException(404, "Profile not found")
        return profiles[0]

    def get_agent_sessions(self, profile_id: UUID) -> list[dict]:
        return _execute(
            self._get_client()
            .table("agent_sessions")
            .select("id,profile_id,title,messages,created_at,updated_at")
            .eq("profile_id", str(profile_id))
            .order("updated_at", desc=True)
        )

    def get_agent_session(self, profile_id: UUID, session_id: UUID) -> dict:
        sessions = _execute(
            self._get_client()
            .table("agent_sessions")
            .select("id,profile_id,title,messages,created_at,updated_at")
            .eq("id", str(session_id))
            .eq("profile_id", str(profile_id))
            .limit(1)
        )
        if not sessions:
            raise HTTPException(404, "Agent session not found")
        return sessions[0]

    def create_agent_session(
        self,
        profile_id: UUID,
        messages: dict | list[dict],
        title: str = "New conversation",
    ) -> dict:
        new_messages = messages if isinstance(messages, list) else [messages]
        sessions = _execute(
            self._get_client()
            .table("agent_sessions")
            .insert({
                "profile_id": str(profile_id),
                "title": title,
                "messages": new_messages,
            })
        )
        return sessions[0]

    def update_agent_session(
        self,
        profile_id: UUID,
        session_id: UUID,
        messages: dict | list[dict],
        title: str | None = None,
    ) -> dict:
        new_messages = messages if isinstance(messages, list) else [messages]
        values = {
            "messages": new_messages,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if title is not None:
            values["title"] = title

        sessions = _execute(
            self._get_client()
            .table("agent_sessions")
            .update(values)
            .eq("id", str(session_id))
            .eq("profile_id", str(profile_id))
        )
        if not sessions:
            raise HTTPException(404, "Agent session not found")
        return sessions[0]

    def get_applications(self, profile_id: UUID) -> list[dict]:
        return _execute(
            self._get_client()
            .table("applications")
            .select(
                "id,profile_id,job_id,job_title,company,tailored_cv_text,"
                "status,submitted_at,created_at"
            )
            .eq("profile_id", str(profile_id))
            .order("created_at", desc=True)
        )

    def get_application_for_job(self, profile_id: UUID, job_id: str) -> dict:
        applications = _execute(
            self._get_client()
            .table("applications")
            .select(
                "id,profile_id,job_id,job_title,company,tailored_cv_text,"
                "status,submitted_at,created_at"
            )
            .eq("profile_id", str(profile_id))
            .eq("job_id", job_id)
            .order("created_at", desc=True)
            .limit(1)
        )
        if not applications:
            raise HTTPException(404, "Application not found for this job")
        return applications[0]

    def save_draft_application(
        self,
        profile_id: UUID,
        job_id: str,
        job_title: str,
        company: str,
        tailored_cv_text: str,
    ) -> dict:
        client = self._get_client()
        existing = _execute(
            client
            .table("applications")
            .select("id")
            .eq("profile_id", str(profile_id))
            .eq("job_id", job_id)
            .eq("status", "draft")
            .limit(1)
        )
        values = {
            "job_title": job_title,
            "company": company,
            "tailored_cv_text": tailored_cv_text,
            "status": "draft",
        }

        if existing:
            applications = _execute(
                client
                .table("applications")
                .update(values)
                .eq("id", existing[0]["id"])
                .eq("profile_id", str(profile_id))
            )
        else:
            applications = _execute(
                client
                .table("applications")
                .insert({
                    "id": str(uuid4()),
                    "profile_id": str(profile_id),
                    "job_id": job_id,
                    **values,
                })
            )
        return applications[0]

    def get_jobs(self) -> list[dict]:
        return self._jobs.get_jobs()

    def get_job(self, job_id: str) -> dict:
        return self._jobs.get_job(job_id)

    def set_application_status(
        self,
        profile_id: UUID,
        application_id: UUID,
        status: str,
    ) -> dict:
        if status not in APPLICATION_STATUSES:
            raise ValueError(f"Unsupported application status: {status}")
        values = {"status": status}
        if status == "pending":
            values["submitted_at"] = datetime.now(timezone.utc).isoformat()

        applications = _execute(
            self._get_client()
            .table("applications")
            .update(values)
            .eq("id", str(application_id))
            .eq("profile_id", str(profile_id))
        )
        if not applications:
            raise HTTPException(404, "Application not found")
        return applications[0]

    def get_emails(
        self,
        profile_id: UUID,
        direction: str | None = None,
        application_id: UUID | None = None,
    ) -> list[dict]:
        query = (
            self._get_client()
            .table("emails")
            .select(
                "id,application_id,direction,type,subject,body,created_at,"
                "applications!inner(profile_id)"
            )
            .eq("applications.profile_id", str(profile_id))
        )
        if direction:
            query = query.eq("direction", direction)
        if application_id:
            query = query.eq("application_id", str(application_id))
        return _execute(query.order("created_at", desc=True))

    def add_email(
        self,
        profile_id: UUID,
        application_id: UUID,
        direction: str,
        email_type: str,
        subject: str,
        body: str,
    ) -> dict:
        applications = _execute(
            self._get_client()
            .table("applications")
            .select("id")
            .eq("id", str(application_id))
            .eq("profile_id", str(profile_id))
            .limit(1)
        )
        if not applications:
            raise HTTPException(404, "Application not found")

        emails = _execute(
            self._get_client()
            .table("emails")
            .insert({
                "application_id": str(application_id),
                "direction": direction,
                "type": email_type,
                "subject": subject,
                "body": body,
            })
        )
        return emails[0]

    def get_calendar_events(
        self,
        profile_id: UUID,
        application_id: UUID | None = None,
        future_only: bool = False,
    ) -> list[dict]:
        query = (
            self._get_client()
            .table("calendar_events")
            .select(
                "id,application_id,event_type,title,description,"
                "starts_at,ends_at,status,applications!inner(profile_id)"
            )
            .eq("applications.profile_id", str(profile_id))
        )
        if application_id:
            query = query.eq("application_id", str(application_id))
        if future_only:
            query = query.gte("starts_at", datetime.now(timezone.utc).isoformat())
        return _execute(query.order("starts_at"))

    def add_calendar_event(
        self,
        profile_id: UUID,
        application_id: UUID,
        event_type: str,
        title: str,
        description: str | None,
        starts_at: datetime,
        ends_at: datetime,
    ) -> dict:
        if event_type not in CALENDAR_EVENT_TYPES:
            raise ValueError(f"Unsupported calendar event type: {event_type}")
        applications = _execute(
            self._get_client()
            .table("applications")
            .select("id")
            .eq("id", str(application_id))
            .eq("profile_id", str(profile_id))
            .limit(1)
        )
        if not applications:
            raise HTTPException(404, "Application not found")

        events = _execute(
            self._get_client()
            .table("calendar_events")
            .insert({
                "application_id": str(application_id),
                "event_type": event_type,
                "title": title,
                "description": description,
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "status": "scheduled",
            })
        )
        return events[0]

    def update_calendar_event(
        self,
        profile_id: UUID,
        calendar_event_id: UUID,
        starts_at: datetime | None = None,
        duration_minutes: int | None = None,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> dict:
        if status is not None and status not in CALENDAR_EVENT_STATUSES:
            raise ValueError(f"Unsupported calendar event status: {status}")
        events = _execute(
            self._get_client()
            .table("calendar_events")
            .select(
                "id,starts_at,ends_at,applications!inner(profile_id)"
            )
            .eq("id", str(calendar_event_id))
            .eq("applications.profile_id", str(profile_id))
            .limit(1)
        )
        if not events:
            raise HTTPException(404, "Calendar event not found")

        values = {}
        if starts_at is not None or duration_minutes is not None:
            current_start = datetime.fromisoformat(
                events[0]["starts_at"].replace("Z", "+00:00")
            )
            current_end = datetime.fromisoformat(
                events[0]["ends_at"].replace("Z", "+00:00")
            )
            new_start = starts_at or current_start
            duration = (
                timedelta(minutes=duration_minutes)
                if duration_minutes is not None
                else current_end - current_start
            )
            values["starts_at"] = new_start.isoformat()
            values["ends_at"] = (new_start + duration).isoformat()
        if title is not None:
            values["title"] = title
        if description is not None:
            values["description"] = description
        if status is not None:
            values["status"] = status

        updated_events = _execute(
            self._get_client()
            .table("calendar_events")
            .update(values)
            .eq("id", str(calendar_event_id))
        )
        return updated_events[0]


database = Database()
