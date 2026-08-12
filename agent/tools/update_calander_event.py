from datetime import datetime
from typing import Type
from uuid import UUID

from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from api.db import database as db


class UpdateCalanderEventInput(BaseModel):
    calendar_event_id: UUID = Field(description="the calendar event to update")
    starts_at: datetime | None = Field(
        default=None,
        description="new start time including timezone",
    )
    duration_minutes: int | None = Field(
        default=None,
        gt=0,
        description="new event duration in minutes",
    )
    title: str | None = Field(default=None, description="new event title")
    description: str | None = Field(default=None, description="new event description")


class UpdateCalanderEvent(BaseTool):
    name: str = "update_calander_event"
    description: str = "reschedules or edits an existing calendar event"
    args_schema: Type[BaseModel] = UpdateCalanderEventInput

    def _run(
        self,
        calendar_event_id: UUID,
        starts_at: datetime | None = None,
        duration_minutes: int | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> ToolResponse:
        if starts_at is not None and starts_at.tzinfo is None:
            raise ValueError("starts_at must include a timezone")
        if all(
            value is None
            for value in (starts_at, duration_minutes, title, description)
        ):
            raise ValueError("at least one field must be provided")

        event = db.update_calendar_event(
            profile_id=self.profile_id,
            calendar_event_id=calendar_event_id,
            starts_at=starts_at,
            duration_minutes=duration_minutes,
            title=title,
            description=description,
        )
        return ToolResponse(content=event)
