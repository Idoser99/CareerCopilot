from typing import Literal, Type
from uuid import UUID

from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from api.db import database as db


class SendEmailInput(BaseModel):
    application_id: UUID = Field(description="the related application")
    subject: str = Field(description="the email subject")
    body: str = Field(description="the email body")
    type: Literal["submitted", "accepted", "rejected", "confirmation"] = Field(
        description="the email type"
    )


class SendEmail(BaseTool):
    name: str = "send_email"
    description: str = "sends an outbound email related to an application"
    args_schema: Type[BaseModel] = SendEmailInput

    def _run(
        self,
        application_id: UUID,
        subject: str,
        body: str,
        type: str,
    ) -> ToolResponse:
        email = db.add_email(
            profile_id=self.profile_id,
            application_id=application_id,
            direction="outbound",
            email_type=type,
            subject=subject,
            body=body,
        )
        return ToolResponse(content=email)
