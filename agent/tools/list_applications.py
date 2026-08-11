from typing import Type

from pydantic import BaseModel

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from api.db import database as db


class ListApplicationsInput(BaseModel):
    pass


class ListApplications(BaseTool):
    name: str = "list_applications"
    description: str = "lists all applications for the active profile"
    args_schema: Type[BaseModel] = ListApplicationsInput

    def _run(self) -> ToolResponse:
        return ToolResponse(content=db.get_applications(self.profile_id))
