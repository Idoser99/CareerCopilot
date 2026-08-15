import json
import os
from uuid import UUID

from langchain_openai import ChatOpenAI

from agent.agent import Agent
from agent.agent_session import AgentSession
from agent.registry import create_registry
from data.db import database as db


class InboundEmailService:
    """agent trigger for an inbound email, runs when an email arrives and process it,
    decide what to do and adds a notification so the user will know what happened"""
    def __init__(self, llm=None):
        self.llm = llm

    def process_inbound_email(self, profile_id: UUID, email_id: UUID) -> dict:
        agent = Agent(self.llm or self._create_llm(), create_registry(profile_id))
        response = agent.invoke(
            prompt=self._create_prompt(email_id),
            session=AgentSession(),
        )
        title, message = self._parse_notification(response.content)
        return db.add_notification(
            profile_id=profile_id,
            title=title,
            message=message,
        )

    @staticmethod
    def _create_llm():
        model_prefix = os.getenv("OPENAI_MODEL_PREFIX")
        if not model_prefix:
            raise ValueError("OPENAI_MODEL_PREFIX is not configured")
        return ChatOpenAI(model=f"{model_prefix}-gpt-5-mini")

    @staticmethod
    def _create_prompt(email_id: UUID) -> str:
        return f"""
Automation trigger: a new inbound employer email with ID {email_id} was
received. The user authorized automatic interview scheduling for this demo.

Read the email and its related application. Record an accepted or rejected
decision only when it is explicit. If the email offers interview times, compare
them with future calendar events, choose the earliest conflict-free slot, send an
outbound confirmation, and schedule the interview. If none are available,
request alternative times and leave the application accepted. If rejected, do
not send email or schedule an event.

After all tool actions, return only valid JSON with this structure:
{{"title": "short title", "message": "one or two short sentences"}}
The title must be at most 60 characters and the message at most 180 characters.
Describe only actions that actually succeeded. Do not include IDs or Markdown.
""".strip()

    @staticmethod
    def _parse_notification(content: str) -> tuple[str, str]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        try:
            notification = json.loads(text)
            title = str(notification.get("title") or "Application update")
            message = str(notification.get("message") or "")
        except (json.JSONDecodeError, AttributeError):
            title = "Application update"
            message = " ".join(text.split())

        title = title.strip() or "Application update"
        message = message.strip() or "CareerCopilot processed the new email."
        return title[:60], message[:180]


inbound_email_service = InboundEmailService()
