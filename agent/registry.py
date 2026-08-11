from uuid import UUID

from agent.tools.base_tool import BaseTool
from agent.tools.list_applications import ListApplications
from agent.tools.list_emails import ListEmails
from agent.tools.schedule_interview import ScheduleInterview
from agent.tools.send_email import SendEmail
from agent.tools.tailor_cv import TailorCV
from agent.tools.search_jobs import SearchJobs
from agent.tools.submit_application import SubmitApplication


class ToolRegistry:
    def __init__(self, tools: [BaseTool]):
        self.tools = {
            tool.name: tool
            for tool in tools
        }

    def get(self, name) -> BaseTool:
        return self.tools.get(name)

    def get_all(self) -> [BaseTool]:
        return self.tools.values()


def create_registry(profile_id: UUID) -> ToolRegistry:
    return ToolRegistry([
        ListApplications(profile_id=profile_id),
        ListEmails(profile_id=profile_id),
        ScheduleInterview(profile_id=profile_id),
        SendEmail(profile_id=profile_id),
        TailorCV(profile_id=profile_id),
        SearchJobs(profile_id=profile_id),
        SubmitApplication(profile_id=profile_id)
    ])
