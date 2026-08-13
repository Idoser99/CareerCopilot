from typing import Type
from uuid import UUID

from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from api.db import database as db


class ListCalanderEventsInput(BaseModel):
    application_id: UUID | None = Field(
        default=None,
        description="optionally filter events by application",
    )
    future_only: bool = Field(
        default=False,
        description="return only events that start in the future",
    )


class ListCalanderEvents(BaseTool):
    name: str = "list_calander_events"
    description: str = "lists calendar events for the active profile"
    args_schema: Type[BaseModel] = ListCalanderEventsInput

    def _run(
        self,
        application_id: UUID | None = None,
        future_only: bool = False,
    ) -> ToolResponse:
        events = db.get_calendar_events(
            profile_id=self.profile_id,
            application_id=application_id,
            future_only=future_only,
        )
        return ToolResponse(content=events)
