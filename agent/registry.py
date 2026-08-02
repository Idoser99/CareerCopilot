from agent.tools.base_tool import BaseTool
from agent.tools.schedule_interview import ScheduleInterview
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


def create_registry() -> ToolRegistry:
    return ToolRegistry([
        ScheduleInterview(),
        TailorCV(),
        SearchJobs(),
        SubmitApplication()
    ])
