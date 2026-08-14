from typing import Type
from uuid import UUID

from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from data.db import database as db


class WithdrawApplicationInput(BaseModel):
    application_id: UUID = Field(description="application to withdraw")


class WithdrawApplication(BaseTool):
    name: str = "withdraw_application"
    description: str = (
        "withdraws an application for the active profile only when the user "
        "explicitly asks to withdraw it"
    )
    args_schema: Type[BaseModel] = WithdrawApplicationInput

    def _run(self, application_id: UUID) -> ToolResponse:
        application = db.set_application_status(
            profile_id=self.profile_id,
            application_id=application_id,
            status="withdrawn",
        )
        return ToolResponse(content={
            "message": "Application withdrawn successfully",
            "application_id": str(application_id),
            "status": application["status"]
        })
