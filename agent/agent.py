from langchain_openai import ChatOpenAI

from agent.agent_response import AgentResponse
from agent.registry import ToolRegistry
from agent.agent_session import AgentSession
from agent.tools.tool_response import ToolResponse
from api.schemas import ExecutionStep


class Agent:
    def __init__(self, llm: ChatOpenAI, registry: ToolRegistry, max_iterations: int = 7):
        self.llm = llm.bind_tools(registry.get_all())
        self.tools_registry = registry
        self.max_iterations = max_iterations

    def invoke(self, prompt: str, session: AgentSession | None = None) -> AgentResponse:
        # initializing a new session only wasn't supplied
        session = session or AgentSession()
        session.add_user_message(prompt)

        # initializing steps list
        steps: list[ExecutionStep] = []

        # starting the ReAct agent loop
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # llm raw response based on session history
            prompt_msgs = [message.model_dump() for message in session.messages]
            formatted_prompt_msgs = AgentSession.format_messages(session.messages)
            response = self.llm.invoke(prompt_msgs)
            session.add_ai_message(response)
            formatted_response = AgentSession.format_messages([response])[0]
            steps.append(ExecutionStep(
                module="CareerCopilot",
                prompt={"messages": formatted_prompt_msgs},
                response=formatted_response,
            ))

            # if agent did not request any tool then return
            if not response.tool_calls:
                return AgentResponse(content=response.content, steps=steps)

            # find requested tools
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]

                # get tool from registry
                tool = self.tools_registry.get(tool_name)

                tool_response: ToolResponse
                try:
                    # trying to invoke the tool
                    tool_response = tool.invoke(tool_args)
                except Exception as e:
                    tool_response = ToolResponse(content=f"Error executing tool {tool_name}: {str(e)}")

                session.add_tool_message(content=tool_response.content, tool_call_id=tool_call_id)
                steps.extend(tool_response.steps)

        return AgentResponse(content="CareerCopilot agent reached maximum iterations. Please try to break down your "
                                     "request into smaller ones",
                             steps=steps)
