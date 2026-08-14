from agent.tools.base_tool import BaseTool
from typing import Type
from uuid import UUID

from pydantic import BaseModel, Field

from agent.tools.tool_response import ToolResponse
from data.db import database as db


class SubmitApplicationInput(BaseModel):
    application_id: UUID = Field(description="the application to submit")


class SubmitApplication(BaseTool):
    name: str = "submit_application"
    description: str = "submits an existing application"
    args_schema: Type[BaseModel] = SubmitApplicationInput

    def _run(self, application_id: UUID) -> ToolResponse:
        application = db.set_application_status(
            profile_id=self.profile_id,
            application_id=application_id,
            status="pending",
        )
        return ToolResponse(content={
            "message": "Application submitted successfully",
            "application_id": str(application_id),
            "status": application["status"],
            "submitted_at": application["submitted_at"],
        })
