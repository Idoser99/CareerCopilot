"""LLM-backed tool for comparing a candidate's CV with a specific job."""

import json
import os
from typing import Annotated, Any, Literal, Type

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StringConstraints,
)

from agent.tools.base_tool import BaseTool
from agent.agent_session import AgentSession
from agent.tools.tool_response import ToolResponse
from data.db import database as db
from api.schemas import ExecutionStep


NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
Priority = Literal["High", "Medium", "Low"]


class SkillGapModel(BaseModel):
    """Strict base model shared by the analyzer's input and output schemas."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SkillGapAnalyzerInput(SkillGapModel):
    job_id: NonEmptyText = Field(description="ID of the target job")


class StrongSkill(SkillGapModel):
    skill_name: NonEmptyText
    evidence_from_cv: NonEmptyText
    relevance_to_job: NonEmptyText


class SkillToStrengthen(SkillGapModel):
    skill_name: NonEmptyText
    evidence_from_cv: NonEmptyText
    what_is_lacking: NonEmptyText
    priority: Priority


class MissingSkill(SkillGapModel):
    skill_name: NonEmptyText
    why_it_matters: NonEmptyText
    priority: Priority


class SkillGapAnalysis(SkillGapModel):
    strong_skills: list[StrongSkill]
    skills_to_strengthen: list[SkillToStrengthen]
    missing_skills: list[MissingSkill]


SKILL_GAP_ANALYZER_PROMPT = """
You are the Skill Gap Analyzer for CareerCopilot. Compare the supplied candidate
CV only against the supplied target job description.

Classify each meaningful, job-relevant skill in one category only; never repeat a
skill across categories:
- Strong skills: clearly demonstrated in the CV at a level that meets or strongly
  supports the job requirement.
- Skills to strengthen: present or reasonably evidenced in the CV, but not
  demonstrated at the depth or level the job appears to require.
- Missing skills: important requirements or strong preferences with no meaningful
  evidence in the CV.

Analyze semantically rather than relying only on exact keyword matches. A related
technology may support a careful inference, but every conclusion about the
candidate must remain grounded in the CV. Consider the amount and type of evidence;
a single technology mention does not prove proficiency.

Prioritize gaps according to their importance to this specific job. Core, explicit
requirements should normally rank above minor or preferred qualifications. Do not
invent candidate experience, job requirements, or irrelevant minor gaps. Do not
produce a match score, hiring recommendation, or generic candidate assessment.

For every strong skill, provide the skill name, CV evidence, and relevance to the
job. For every skill to strengthen, provide the skill name, existing CV evidence,
what is lacking, and a High, Medium, or Low priority. For every missing skill,
provide the skill name, why it matters to the job, and a High, Medium, or Low
priority. Return only information supported by the supplied context.
""".strip()


def _build_messages(
    job_description: str,
    cv: str,
) -> list[SystemMessage | HumanMessage]:
    context = json.dumps(
        {"job_description": job_description, "cv": cv},
        ensure_ascii=False,
    )
    return [
        SystemMessage(content=SKILL_GAP_ANALYZER_PROMPT),
        HumanMessage(
            content=(
                "Analyze the following JSON object as context and return the "
                f"required skill-gap analysis:\n{context}"
            )
        ),
    ]


class SkillGapAnalyzer(BaseTool):
    name: str = "skill_gap_analyzer"
    description: str = (
        "Compare a job with its application's tailored CV and the profile's "
        "original CV, selected by job ID, and "
        "return structured strong skills, skills to strengthen, and missing skills. "
        "Use this for job-specific skill-gap analysis, not candidate scoring."
    )
    args_schema: Type[BaseModel] = SkillGapAnalyzerInput

    _llm: Any = PrivateAttr(default=None)

    def __init__(self, llm: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm = llm

    def _get_llm(self) -> Any:
        if self._llm is None:
            load_dotenv()
            model_prefix = os.getenv("OPENAI_MODEL_PREFIX")
            if not model_prefix:
                raise ValueError("OPENAI_MODEL_PREFIX is not configured")
            self._llm = ChatOpenAI(model=f"{model_prefix}-gpt-5-mini")
        return self._llm

    def _run(self, job_id: str) -> ToolResponse:
        request = SkillGapAnalyzerInput.model_validate({"job_id": job_id})
        job = db.get_job(request.job_id)
        profile = db.get_profile(self.profile_id)
        application = db.get_application_for_job(self.profile_id, request.job_id)
        job_description = json.dumps(
            {
                "job_id": job.get("job_id"),
                "title": job.get("title"),
                "description": job.get("description"),
                "skills": job.get("skills"),
            },
            ensure_ascii=False,
        )
        tailored_cv = application.get("tailored_cv_text")
        if not isinstance(tailored_cv, str) or not tailored_cv.strip():
            raise ValueError("The application does not have a tailored CV")
        cv = json.dumps(
            {
                "tailored_cv": tailored_cv,
                "original_profile_cv": profile.get("cv_text") or None,
            },
            ensure_ascii=False,
        )

        messages = _build_messages(job_description, cv)

        structured_llm = self._get_llm().with_structured_output(SkillGapAnalysis)
        raw_analysis = structured_llm.invoke(messages)
        analysis = SkillGapAnalysis.model_validate(raw_analysis)
        content = analysis.model_dump(mode="json")

        return ToolResponse(
            content=content,
            steps=[
                ExecutionStep(
                    module="Skill Gap Analyzer",
                    prompt={"messages": AgentSession.format_messages(messages)},
                    response={"role": "assistant", "content": content},
                )
            ],
        )
