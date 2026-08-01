from api.schemas import ExecutionStep
from pydantic import BaseModel


class AgentResponse(BaseModel):
    """agent response = returns the raw final response and the list of steps(including submodules) used throughout the
    agent session"""
    content: str
    steps: list[ExecutionStep] = []
