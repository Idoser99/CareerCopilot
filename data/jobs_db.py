import json
from pathlib import Path

from fastapi import HTTPException


JOBS_FILE = Path(__file__).resolve().parents[1] / "data" / (
    "linkedin_like_simulated_jobs_tech_focused.json"
)


class JobsDatabase:
    def __init__(self):
        self._jobs: list[dict] | None = None

    def _load_jobs(self) -> list[dict]:
        if self._jobs is not None:
            return self._jobs

        try:
            with JOBS_FILE.open(encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise HTTPException(500, "Jobs database could not be loaded") from error

        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise HTTPException(500, "Jobs database has an invalid structure")

        self._jobs = [job for job in data["jobs"] if isinstance(job, dict)]
        return self._jobs

    def get_jobs(self) -> list[dict]:
        return self._load_jobs()

    def get_job(self, job_id: str) -> dict:
        job_id = job_id.strip()
        for job in self._load_jobs():
            if str(job.get("job_id") or "") == job_id:
                return job
        raise HTTPException(404, "Job not found")
