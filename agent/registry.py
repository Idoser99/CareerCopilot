from uuid import UUID

from agent.tools.base_tool import BaseTool
from agent.tools.get_profile_cv import GetProfileCV
from agent.tools.preparation_plan import PreparationPlan
from agent.tools.skill_gap_analyzer import SkillGapAnalyzer
from agent.tools.write_cv import WriteCV
from agent.tools.list_applications import ListApplications
from agent.tools.list_calander_events import ListCalanderEvents
from agent.tools.list_emails import ListEmails
from agent.tools.schedule_calander_event import ScheduleCalanderEvent
from agent.tools.send_email import SendEmail
from agent.tools.tailor_cv import TailorCV
from agent.tools.search_jobs import SearchJobs
from agent.tools.submit_application import SubmitApplication
from agent.tools.update_calander_event import UpdateCalanderEvent


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
        GetProfileCV(profile_id=profile_id),
        PreparationPlan(profile_id=profile_id),
        SkillGapAnalyzer(profile_id=profile_id),
        WriteCV(profile_id=profile_id),
        ListApplications(profile_id=profile_id),
        ListCalanderEvents(profile_id=profile_id),
        ListEmails(profile_id=profile_id),
        ScheduleCalanderEvent(profile_id=profile_id),
        SendEmail(profile_id=profile_id),
        TailorCV(profile_id=profile_id),
        SearchJobs(profile_id=profile_id),
        SubmitApplication(profile_id=profile_id),
        UpdateCalanderEvent(profile_id=profile_id)
    ])
