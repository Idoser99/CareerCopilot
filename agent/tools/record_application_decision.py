from typing import Literal, Type
from uuid import UUID

from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from data.db import database as db


class RecordApplicationDecisionInput(BaseModel):
    email_id: UUID = Field(description="inbound email containing the decision")
    decision: Literal["accepted", "rejected"] = Field(
        description="explicit employer decision stated in the email"
    )


class RecordApplicationDecision(BaseTool):
    name: str = "record_application_decision"
    description: str = (
        "records an accepted or rejected decision explicitly stated in an inbound "
        "employer email; never use it based on a guess"
    )
    args_schema: Type[BaseModel] = RecordApplicationDecisionInput

    def _run(self, email_id: UUID, decision: str) -> ToolResponse:
        email = db.get_email(self.profile_id, email_id)
        if email["direction"] != "inbound":
            raise ValueError("Application decisions must come from inbound email")
        if email["type"] != decision:
            raise ValueError("Decision does not match the inbound email")

        application = db.set_application_status(
            profile_id=self.profile_id,
            application_id=UUID(str(email["application_id"])),
            status=decision,
        )
        return ToolResponse(content={
            "application_id": application["id"],
            "status": application["status"],
            "source_email_id": str(email_id),
        })
