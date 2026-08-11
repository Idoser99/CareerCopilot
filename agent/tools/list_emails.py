from typing import Literal, Type
from uuid import UUID

from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from api.db import database as db


class ListEmailsInput(BaseModel):
    direction: Literal["inbound", "outbound"] | None = Field(
        default=None,
        description="optionally filter emails by direction",
    )
    application_id: UUID | None = Field(
        default=None,
        description="optionally filter emails by application",
    )


class ListEmails(BaseTool):
    name: str = "list_emails"
    description: str = "lists emails for the active profile with optional filters"
    args_schema: Type[BaseModel] = ListEmailsInput

    def _run(
        self,
        direction: str | None = None,
        application_id: UUID | None = None,
    ) -> ToolResponse:
        emails = db.get_emails(
            profile_id=self.profile_id,
            direction=direction,
            application_id=application_id,
        )
        return ToolResponse(content=emails)
