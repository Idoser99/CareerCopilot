from abc import abstractmethod

import langchain.tools
from agent.tools.tool_response import ToolResponse


class BaseTool(langchain.tools.BaseTool):
    @abstractmethod
    def _run(self, **kwargs) -> ToolResponse:
        """forcing tools to return a ToolResponse instance"""
        pass
