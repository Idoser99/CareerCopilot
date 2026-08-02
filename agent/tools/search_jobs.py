from agent.tools.base_tool import BaseTool
from typing import Type
from pydantic import BaseModel, Field

from agent.tools.tool_response import ToolResponse


class JobSummary(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    key_skills: list[str]


class SearchJobsInput(BaseModel):
    keyword: str = Field(description="keyword to search jobs based on")


class SearchJobs(BaseTool):
    name: str = "search_jobs"
    description: str = "gets a keyword like a job title and return a list of jobs matching that keyword"
    args_schema: Type[BaseModel] = SearchJobsInput

    def _run(self, keyword) -> ToolResponse:
        return ToolResponse(content=[
            JobSummary(job_id="job_1", title="jave developer", company="google", location="Tel Aviv",
                       key_skills=["2 years hands on java development", "REST API backend - advantage"]).model_dump(),
            JobSummary(job_id="job_2", title="C developer", company="AWS", location="Beer Sheva",
                       key_skills=["2 years hands on C development", "building kernels for edge devices with custom OS", "assembly - advantage"]).model_dump()
        ])
