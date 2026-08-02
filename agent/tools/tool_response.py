from api.schemas import ExecutionStep
from pydantic import BaseModel
from typing import Any


class ToolResponse(BaseModel):
    """tool response schema - allowing to return execution steps if the tool used an llm"""
    content: Any
    steps: list[ExecutionStep] = []
