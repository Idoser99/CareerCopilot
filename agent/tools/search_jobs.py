"""Tool that searches the simulated jobs database."""

import json
import math
import re
from pathlib import Path
from typing import Any, Type

from agent.tools.base_tool import BaseTool
from pydantic import BaseModel, Field

from agent.tools.tool_response import ToolResponse

JOBS_FILE = Path(__file__).resolve().parents[2] / "data" / (
    "linkedin_like_simulated_jobs_tech_focused.json"
)


class JobSummary(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    workplace_type: str
    employment_type: str
    seniority_level: str
    date_posted: str
    key_skills: list[str]
    description: str
    required_qualifications: list[str]
    preferred_qualifications: list[str]
    match_score: int
    application_url: str | None


class SearchJobsInput(BaseModel):
    keyword: str = Field(
        min_length=1,
        description="Wanted job title, for example 'backend developer'",
    )
    locations: list[str] = Field(
        default_factory=list, description="Accepted cities or countries"
    )
    workplace_types: list[str] = Field(
        default_factory=list, description="Remote, Hybrid, or On-site"
    )
    seniority_levels: list[str] = Field(
        default_factory=list, description="For example Entry level or Associate"
    )
    employment_types: list[str] = Field(
        default_factory=list, description="For example Full-time or Internship"
    )
    companies: list[str] = Field(
        default_factory=list, description="Only return these companies when supplied"
    )
    excluded_job_ids: list[str] = Field(
        default_factory=list, description="Job IDs that must not be returned"
    )
    minimum_score: float = Field(default=1, ge=0, le=70)
    max_results: int = Field(default=10, ge=1, le=50)


def normalize(value: Any) -> str:
    """Make text lowercase and remove unnecessary punctuation and spaces."""
    if not isinstance(value, str):
        return ""
    value = value.lower().strip().replace("-", " ").replace("_", " ")
    return " ".join(re.sub(r"[^\w+#.]+", " ", value).split())


def get_value(job: dict, *keys: str) -> Any:
    """Read a nested value without crashing when a field is missing."""
    value = job
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def get_title_score(job_title: str, wanted_titles: list[str]) -> int:
    """Give more points to better title matches."""
    job_title = normalize(job_title)
    best_score = 0
    if not job_title:
        return best_score

    for wanted_title in wanted_titles:
        wanted_title = normalize(wanted_title)
        if job_title == wanted_title:
            score = 35
        elif wanted_title in job_title or job_title in wanted_title:
            score = 30
        else:
            words = set(wanted_title.split())
            shared = words & set(job_title.split())
            # One generic shared word such as "developer" is too weak.
            score = round(25 * len(shared) / len(words)) if len(shared) >= 2 else 0

        if score > best_score:
            best_score = score
    return best_score


def find_relevant_jobs(preferences: dict, max_results: int = 10) -> list[dict]:
    """Load, filter, score, and rank jobs according to the PRD."""
    if not isinstance(preferences, dict):
        raise TypeError("preferences must be a dictionary")
    if not isinstance(max_results, int) or isinstance(max_results, bool):
        raise TypeError("max_results must be an integer")
    if max_results < 0:
        raise ValueError("max_results cannot be negative")

    fields = (
        "job_titles", "locations", "workplace_types", "seniority_levels",
        "employment_types", "companies", "excluded_job_ids",
    )
    wanted = {}
    for field in fields:
        values = preferences.get(field, []) or []
        if not isinstance(values, list) or not all(isinstance(x, str) for x in values):
            raise TypeError(f"preferences['{field}'] must be a list of strings")
        wanted[field] = list({normalize(x): x.strip() for x in values if x.strip()}.values())

    minimum_score = preferences.get("minimum_score", 0)
    if (
        not isinstance(minimum_score, (int, float))
        or isinstance(minimum_score, bool)
        or not math.isfinite(minimum_score)
    ):
        raise TypeError("minimum_score must be a finite number")

    try:
        with JOBS_FILE.open(encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError("The jobs file is not valid JSON") from error
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("The jobs file must contain a 'jobs' list")

    accepted = {
        field: {normalize(value) for value in values}
        for field, values in wanted.items()
    }
    ranked_jobs = []

    for position, job in enumerate(data["jobs"]):
        if not isinstance(job, dict):
            continue

        title = normalize(job.get("title"))
        job_id = normalize(job.get("job_id"))
        workplace = normalize(get_value(job, "location", "workplace_type"))
        seniority = normalize(get_value(job, "employment", "seniority_level"))
        employment = normalize(get_value(job, "employment", "employment_type"))
        company = normalize(get_value(job, "company", "name"))
        location = normalize(" ".join(
            str(get_value(job, "location", key) or "")
            for key in ("city", "region", "country", "formatted")
        ))
        wrong_location = accepted["locations"] and not any(
            place in location for place in accepted["locations"]
        )
        wrong_exact_filter = any((
            accepted["workplace_types"] and workplace not in accepted["workplace_types"],
            accepted["seniority_levels"] and seniority not in accepted["seniority_levels"],
            accepted["employment_types"] and employment not in accepted["employment_types"],
            accepted["companies"] and company not in accepted["companies"],
        ))
        if job_id in accepted["excluded_job_ids"]:
            continue
        if wrong_location or wrong_exact_filter:
            continue

        score = get_title_score(title, wanted["job_titles"])
        matched_preferences = ["title"] if score else []

        score_fields = (
            ("locations", 10, "location"),
            ("workplace_types", 5, "workplace"),
            ("seniority_levels", 10, "seniority"),
            ("employment_types", 5, "employment_type"),
        )
        for field, points, label in score_fields:
            if wanted[field]:
                score += points
                matched_preferences.append(label)

        if accepted["companies"] and company in accepted["companies"]:
            score += 5
            matched_preferences.append("company")
        if score < minimum_score:
            continue

        result = {
            **job,
            "match": {
                "score": score,
                "matched_preferences": matched_preferences,
            },
        }

        date_text = str(get_value(job, "posting", "date_posted") or "").replace("-", "")
        posted = int(date_text) if date_text.isdigit() else 0
        applicants = get_value(job, "posting", "applicant_count")
        if not isinstance(applicants, (int, float)) or isinstance(applicants, bool):
            applicants = math.inf
        ranked_jobs.append((result, score, posted, applicants, position))

    # More recent jobs are preferred when relevance scores are equal.
    ranked_jobs.sort(key=lambda item: (-item[1], -item[2], item[3], item[4]))
    return [item[0] for item in ranked_jobs[:max_results]]


def summarize_job(job: dict) -> dict:
    """Create the smaller job object returned by the tool."""
    match = job["match"]
    skills = job.get("skills", [])
    required = get_value(job, "description", "qualifications", "required") or []
    preferred = get_value(job, "description", "qualifications", "preferred") or []
    return JobSummary(
        job_id=str(job.get("job_id") or ""),
        title=str(job.get("title") or ""),
        company=str(get_value(job, "company", "name") or ""),
        location=str(get_value(job, "location", "formatted") or ""),
        workplace_type=str(get_value(job, "location", "workplace_type") or ""),
        employment_type=str(get_value(job, "employment", "employment_type") or ""),
        seniority_level=str(get_value(job, "employment", "seniority_level") or ""),
        date_posted=str(get_value(job, "posting", "date_posted") or ""),
        key_skills=skills if isinstance(skills, list) else [],
        description=str(get_value(job, "description", "summary") or ""),
        required_qualifications=required if isinstance(required, list) else [],
        preferred_qualifications=preferred if isinstance(preferred, list) else [],
        match_score=match["score"],
        application_url=get_value(job, "application", "application_url"),
    ).model_dump()


class SearchJobs(BaseTool):
    name: str = "search_jobs"
    description: str = "Search jobs by title and candidate preferences"
    args_schema: Type[BaseModel] = SearchJobsInput

    def _run(
        self,
        keyword: str,
        locations: list[str] | None = None,
        workplace_types: list[str] | None = None,
        seniority_levels: list[str] | None = None,
        employment_types: list[str] | None = None,
        companies: list[str] | None = None,
        excluded_job_ids: list[str] | None = None,
        minimum_score: float = 1,
        max_results: int = 10,
    ) -> ToolResponse:
        if not keyword.strip():
            raise ValueError("keyword cannot be empty")

        preferences = {
            "job_titles": [keyword],
            "locations": locations or [],
            "workplace_types": workplace_types or [],
            "seniority_levels": seniority_levels or [],
            "employment_types": employment_types or [],
            "companies": companies or [],
            "excluded_job_ids": excluded_job_ids or [],
            "minimum_score": minimum_score,
        }
        jobs = find_relevant_jobs(preferences, max_results=10_000)
        jobs = [
            job for job in jobs if "title" in job["match"]["matched_preferences"]
        ][:max_results]
        return ToolResponse(content=[summarize_job(job) for job in jobs])
