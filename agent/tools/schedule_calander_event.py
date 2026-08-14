from datetime import datetime, timedelta
from typing import Literal, Type
from uuid import UUID

from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from data.db import database as db


class ScheduleCalanderEventInput(BaseModel):
    application_id: UUID = Field(description="the related application")
    event_type: Literal["interview", "preparation"] = Field(
        description="interview appointment or preparation time"
    )
    title: str = Field(description="the event title")
    description: str | None = Field(default=None, description="the event description")
    starts_at: datetime = Field(description="event start time including timezone")
    duration_minutes: int = Field(gt=0, description="event duration in minutes")


class ScheduleCalanderEvent(BaseTool):
    name: str = "schedule_calander_event"
    description: str = (
        "schedules an interview or preparation calendar event for an application"
    )
    args_schema: Type[BaseModel] = ScheduleCalanderEventInput

    def _run(
        self,
        application_id: UUID,
        event_type: str,
        title: str,
        starts_at: datetime,
        duration_minutes: int,
        description: str | None = None,
    ) -> ToolResponse:
        if starts_at.tzinfo is None:
            raise ValueError("starts_at must include a timezone")

        event = db.add_calendar_event(
            profile_id=self.profile_id,
            application_id=application_id,
            event_type=event_type,
            title=title,
            description=description,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=duration_minutes),
        )
        if event_type == "interview":
            db.set_application_status(
                profile_id=self.profile_id,
                application_id=application_id,
                status="scheduled",
            )
        return ToolResponse(content=event)
