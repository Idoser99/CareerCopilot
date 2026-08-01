from agent.tools.base_tool import BaseTool
from typing import Type
from pydantic import BaseModel, Field

from agent.tools.tool_response import ToolResponse


class SubmitApplicationInput(BaseModel):
    cv: str = Field(description="a cv to submit")
    job_id: int = Field(description="a job id to submit the cv to")


class SubmitApplication(BaseTool):
    name: str = "submit_application"
    description: str = "gets a cv and a job id and submits the cv for that job"
    args_schema: Type[BaseModel] = SubmitApplicationInput

    def _run(self, cv: str, job_id: int) -> ToolResponse:
        return ToolResponse(content=f"cv was submitted successfully for job id: {job_id}\n"
                                    f"decision: accepted as a candidate, please schedule an interview")
