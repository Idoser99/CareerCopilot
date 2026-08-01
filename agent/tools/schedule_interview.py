from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class ScheduleInterviewInput(BaseModel):
    job_id: int = Field(description="the job_id to schedule an interview for")


class ScheduleInterview(BaseTool):
    name: str = "schedule_interview"
    description: str = ("gets a job_id to schedule an interview for and returns the time set for the interview\n"
                        "calling this tool again will automatically reschedule the interview if existed")
    args_schema: Type[BaseModel] = ScheduleInterviewInput

    def _run(self, job_id) -> str:
        return f"the interview scheduled for Jan 1, 2027"
