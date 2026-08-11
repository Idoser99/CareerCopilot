import os
from datetime import datetime, timezone
from uuid import UUID

from dotenv import load_dotenv
from fastapi import HTTPException
from supabase import Client, create_client


load_dotenv()


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

    def set_application_status(
        self,
        profile_id: UUID,
        application_id: UUID,
        status: str,
    ) -> dict:
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

    def get_calendar_events(self, profile_id: UUID) -> list[dict]:
        return _execute(
            self._get_client()
            .table("calendar_events")
            .select(
                "id,application_id,event_type,title,description,"
                "starts_at,ends_at,status,applications!inner(profile_id)"
            )
            .eq("applications.profile_id", str(profile_id))
            .order("starts_at")
        )


database = Database()
