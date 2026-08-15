import json
import os

from agent.agent_session import CAREER_COPILOT_SYSTEM_PROMPT
from agent.tools.tailor_cv import TAILOR_CV_PROMPT
from api.schemas import (
    AgentInfoResponse,
    ExecutionStep,
    PromptExample,
    PromptTemplate,
)


def create_agent_info() -> AgentInfoResponse:
    timezone = os.getenv("CAREER_COPILOT_TIMEZONE", "UTC")
    system_message = {
        "role": "system",
        "content": (
            f"{CAREER_COPILOT_SYSTEM_PROMPT}\n\n"
            f"The user's timezone is {timezone}."
        ),
    }
    search_prompt = "Find remote junior software engineering jobs in Israel."
    search_response = (
        "I found a remote Junior Software Engineer role at SAP in Haifa. "
        "It is the strongest match in the current job catalog."
    )
    tailor_prompt = (
        "Tailor my CV for job SIM-0015 and save it as a draft application."
    )
    tailored_cv = (
        "JUNIOR SOFTWARE ENGINEER\n\n"
        "SUMMARY\nPython developer with hands-on backend and API experience.\n\n"
        "SKILLS\nPython, FastAPI, SQL, Git, REST APIs"
    )
    tailor_context = {
        "cv_content": (
            "PYTHON DEVELOPER\n\nSUMMARY\nBackend developer with Python and "
            "API experience.\n\nSKILLS\nPython, FastAPI, SQL, Git"
        ),
        "job_information": json.dumps(
            {
                "job_id": "SIM-0015",
                "title": "Junior Software Engineer",
                "description": {
                    "summary": (
                        "Develop backend services, write tests, review code, "
                        "and support production systems."
                    )
                },
                "skills": [
                    "Python",
                    "Git",
                    "REST APIs",
                    "SQL",
                    "Unit Testing",
                    "Communication",
                ],
                "employment": {
                    "employment_type": "Full-time",
                    "seniority_level": "Entry level",
                },
            },
            ensure_ascii=False,
        ),
        "company_information": json.dumps(
            {
                "name": "SAP",
                "industry": "Enterprise Software",
                "website": "https://www.sap.com",
            },
            ensure_ascii=False,
        ),
    }
    tailor_module_prompt = (
        "Tailor the CV using the following labeled context. Return only the "
        f"complete revised CV:\n{json.dumps(tailor_context, ensure_ascii=False)}"
    )
    tailor_response = (
        "I tailored your CV for the Junior Software Engineer role at SAP and "
        "saved it as a draft application."
    )
    search_tool_call = {
        "name": "search_jobs",
        "args": {
            "keyword": "junior software engineer",
            "locations": ["Israel"],
            "workplace_types": ["Remote"],
            "max_results": 1,
        },
    }
    tailor_tool_call = {
        "name": "tailor_cv",
        "args": {"job_id": "SIM-0015"},
    }

    return AgentInfoResponse(
        description=(
            "CareerCopilot is a profile-aware career workflow agent. Its "
            "CareerCopilot orchestrator uses job, CV, application, email, and "
            "calendar tools together with the Tailor CV, Skill Gap Analyzer, "
            "and Preparation Plan LLM submodules. For demonstration, the "
            "Applications tab can simulate an employer acceptance or rejection "
            "only for applications whose current status is Pending; this creates "
            "an inbound email and triggers the automated response flow."
        ),
        purpose=(
            "Help a job seeker move from job discovery to a tailored CV, "
            "application tracking, employer-email handling, interview "
            "scheduling, skill-gap analysis, and interview preparation while "
            "keeping actions and results connected to the active profile."
        ),
        prompt_template=PromptTemplate(
            template=(
                "Help me [goal or action]. Use my saved profile, CV, "
                "applications, emails, and calendar when relevant. My "
                "preferences or constraints are: [role, location, workplace "
                "type, company, deadline, or available preparation time]. "
                "Before making an external action, follow this instruction: "
                "[find, tailor, submit, email, schedule, analyze, or prepare]."
            )
        ),
        prompt_examples=[
            PromptExample(
                prompt=search_prompt,
                full_response=search_response,
                steps=[
                    ExecutionStep(
                        module="CareerCopilot",
                        prompt={
                            "messages": [
                                system_message,
                                {"role": "user", "content": search_prompt},
                            ]
                        },
                        response={
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [search_tool_call],
                        },
                    ),
                    ExecutionStep(
                        module="CareerCopilot",
                        prompt={
                            "messages": [
                                system_message,
                                {"role": "user", "content": search_prompt},
                                {
                                    "role": "assistant",
                                    "content": "",
                                    "tool_calls": [search_tool_call],
                                },
                                {
                                    "role": "tool",
                                    "name": "search_jobs",
                                    "content": [
                                        {
                                            "job_id": "SIM-0015",
                                            "title": "Junior Software Engineer",
                                            "company": "SAP",
                                            "location": "Haifa, Israel",
                                            "workplace_type": "Remote",
                                            "employment_type": "Full-time",
                                            "seniority_level": "Entry level",
                                            "date_posted": "2026-07-13",
                                            "key_skills": [
                                                "Python",
                                                "Git",
                                                "REST APIs",
                                                "SQL",
                                                "Unit Testing",
                                                "Communication",
                                            ],
                                            "match_score": 50,
                                            "application_url": "https://www.sap.com",
                                        }
                                    ],
                                },
                            ]
                        },
                        response={
                            "role": "assistant",
                            "content": search_response,
                        },
                    ),
                ],
            ),
            PromptExample(
                prompt=tailor_prompt,
                full_response=tailor_response,
                steps=[
                    ExecutionStep(
                        module="CareerCopilot",
                        prompt={
                            "messages": [
                                system_message,
                                {"role": "user", "content": tailor_prompt},
                            ]
                        },
                        response={
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [tailor_tool_call],
                        },
                    ),
                    ExecutionStep(
                        module="Tailor CV",
                        prompt={
                            "messages": [
                                {
                                    "role": "system",
                                    "content": TAILOR_CV_PROMPT,
                                },
                                {
                                    "role": "user",
                                    "content": tailor_module_prompt,
                                },
                            ]
                        },
                        response={
                            "role": "assistant",
                            "content": tailored_cv,
                        },
                    ),
                    ExecutionStep(
                        module="CareerCopilot",
                        prompt={
                            "messages": [
                                system_message,
                                {"role": "user", "content": tailor_prompt},
                                {
                                    "role": "assistant",
                                    "content": "",
                                    "tool_calls": [tailor_tool_call],
                                },
                                {
                                    "role": "tool",
                                    "name": "tailor_cv",
                                    "content": {
                                        "application_id": (
                                            "30000000-0000-0000-0000-000000000015"
                                        ),
                                        "job_id": "SIM-0015",
                                        "job_title": "Junior Software Engineer",
                                        "company": "SAP",
                                        "status": "draft",
                                        "tailored_cv_text": tailored_cv,
                                    },
                                },
                            ]
                        },
                        response={
                            "role": "assistant",
                            "content": tailor_response,
                        },
                    ),
                ],
            ),
        ],
    )
