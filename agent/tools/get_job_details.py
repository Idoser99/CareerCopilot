from typing import Type

from pydantic import BaseModel, Field

from agent.tools.base_tool import BaseTool
from agent.tools.tool_response import ToolResponse
from data.db import database as db


class GetJobDetailsInput(BaseModel):
    job_id: str = Field(min_length=1, description="exact ID of the job")


class GetJobDetails(BaseTool):
    name: str = "get_job_details"
    description: str = "returns the full stored details for one exact job ID"
    args_schema: Type[BaseModel] = GetJobDetailsInput

    def _run(self, job_id: str) -> ToolResponse:
        job = db.get_job(job_id)
        return ToolResponse(content={
            key: value
            for key, value in job.items()
            if key not in {"search_metadata"}
        })
