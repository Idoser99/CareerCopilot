from abc import abstractmethod
from uuid import UUID

import langchain.tools
from agent.tools.tool_response import ToolResponse


class BaseTool(langchain.tools.BaseTool):
    profile_id: UUID

    @abstractmethod
    def _run(self, **kwargs) -> ToolResponse:
        """forcing tools to return a ToolResponse instance"""
        pass
