from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
import json

class AgentSession:
    """tracks the agent session - llm calls, tool calls and responses and user prompts"""

    def __init__(self):
        self.messages: [BaseMessage] = []

    def add_user_message(self, content: str):
        self.messages.append(HumanMessage(content=content))

    def add_ai_message(self, message: AIMessage):
        self.messages.append(message)

    def add_tool_message(self, content, tool_call_id: str):
        tool_response = content
        if not isinstance(content, str):
            tool_response = json.dumps(
                content,
                ensure_ascii=False,
            )
        self.messages.append(ToolMessage(content=tool_response, tool_call_id=tool_call_id))
