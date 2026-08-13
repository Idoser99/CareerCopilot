from typing import Type

from pydantic import BaseModel

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from api.db import database as db


class GetProfileCVInput(BaseModel):
    pass


class GetProfileCV(BaseTool):
    name: str = "get_profile_cv"
    description: str = "returns the CV of the active profile"
    args_schema: Type[BaseModel] = GetProfileCVInput

    def _run(self) -> ToolResponse:
        profile = db.get_profile(self.profile_id)
        return ToolResponse(content=profile.get("cv_text") or "No CV was found")
