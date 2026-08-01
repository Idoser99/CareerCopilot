from langchain_openai import ChatOpenAI
from agent.registry import ToolRegistry
from agent.AgentSession import AgentSession


class Agent:
    def __init__(self, llm: ChatOpenAI, registry: ToolRegistry, max_iterations: int = 5):
        self.llm = llm.bind_tools(registry.get_all())
        self.tools_registry = registry
        self.max_iterations = max_iterations

    def invoke(self, prompt: str, session: AgentSession = None) -> str:
        # initializing the agent session
        if session is None:
            session = AgentSession()
        session.add_user_message(prompt)

        # starting the ReAct agent loop
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # llm raw response based on session history
            response = self.llm.invoke(session.messages)
            session.add_ai_message(response)

            # if agent did not request any tool then return
            if not response.tool_calls:
                return response.content

            # find requested tools
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]

                # get tool from registry
                tool = self.tools_registry.get(tool_name)

                try:
                    # trying to invoke the tool
                    tool_response = tool.invoke(tool_args)
                except Exception as e:
                    tool_response = f"Error executing tool {tool_name}: {str(e)}"

                session.add_tool_message(content=tool_response, tool_call_id=tool_call_id)

        return "CareerCopilot agent reached maximum iterations. Please try to break down your request into smaller ones"
