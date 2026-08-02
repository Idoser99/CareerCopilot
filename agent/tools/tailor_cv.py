from agent.tools.base_tool import BaseTool
from typing import Type
from pydantic import BaseModel, Field

from agent.tools.tool_response import ToolResponse


class TailorCVInput(BaseModel):
    cv: str = Field(description="a general cv to tailor")
    job: str = Field(description="a job description or title to tailor the cv based on")


class TailorCV(BaseTool):
    name: str = "tailor_cv"
    description: str = "gets a cv and a job description and returns a tailored cv"
    args_schema: Type[BaseModel] = TailorCVInput

    def _run(self, cv: str, job: str) -> ToolResponse:
        return ToolResponse(content=f"{cv}\nTailored for {job}")
