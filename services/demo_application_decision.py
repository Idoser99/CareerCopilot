import os
import random
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from data.db import database as db


class DemoApplicationDecisionService:
    def simulate(
        self,
        profile_id: UUID,
        application_id: UUID,
        decision: str,
    ) -> tuple[dict, dict]:
        application = db.get_application(profile_id, application_id)
        profile = db.get_profile(profile_id)
        slots = self._create_interview_slots() if decision == "accepted" else []
        subject, body = self._create_email(profile, application, decision, slots)

        email = db.add_email(
            profile_id=profile_id,
            application_id=application_id,
            direction="inbound",
            email_type=decision,
            subject=subject,
            body=body,
        )
        notification = email.pop("_notification")
        return email, notification

    @staticmethod
    def _create_interview_slots() -> list[datetime]:
        timezone_name = os.getenv("CAREER_COPILOT_TIMEZONE", "UTC")
        current_time = datetime.now(ZoneInfo(timezone_name))
        weekdays = [
            current_time + timedelta(days=days_ahead)
            for days_ahead in range(1, 8)
            if (current_time + timedelta(days=days_ahead)).weekday() < 5
        ]
        possible_slots = [
            day.replace(hour=hour, minute=0, second=0, microsecond=0)
            for day in weekdays
            for hour in (9, 10, 11, 13, 14, 15, 16)
        ]
        return sorted(random.sample(possible_slots, 3))

    @staticmethod
    def _create_email(
        profile: dict,
        application: dict,
        decision: str,
        interview_slots: list[datetime],
    ) -> tuple[str, str]:
        company = application["company"]
        job_title = application["job_title"]
        name = profile["name"]
        if decision == "rejected":
            return (
                f"Application update - {job_title} at {company}",
                f"Hi {name},\n\nThank you for your interest in the {job_title} "
                "role. After careful consideration, we will not be moving "
                f"forward with your application.\n\nBest,\n{company} Hiring Team",
            )

        formatted_slots = "\n".join(
            f"- {slot.strftime('%A, %B %d, %Y at %I:%M %p')} "
            f"({slot.tzinfo}) - 45 minutes"
            for slot in interview_slots
        )
        return (
            f"Interview invitation - {job_title} at {company}",
            f"Hi {name},\n\nWe are pleased to invite you to interview for the "
            f"{job_title} role. Please choose one of these available times:\n\n"
            f"{formatted_slots}\n\nBest,\n{company} Hiring Team",
        )


demo_application_decision_service = DemoApplicationDecisionService()
