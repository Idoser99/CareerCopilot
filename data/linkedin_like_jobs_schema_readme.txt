LinkedIn-Like Simulated Jobs Database

Main JSON structure:
{
  "metadata": {...},
  "jobs": [
    {
      "job_id": "...",
      "source": {...},
      "title": "...",
      "company": {...},
      "location": {...},
      "employment": {...},
      "posting": {...},
      "description": {...},
      "skills": [...],
      "compensation": {...},
      "application": {...},
      "search_metadata": {...}
    }
  ]
}

Important:
- The companies are real.
- Every job posting is fictional and intended only for testing.
- Use dataset["jobs"] to access the list of jobs in Python.
