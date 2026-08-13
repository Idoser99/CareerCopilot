# CareerCopilot

AI agent for managing a job search, with a FastAPI backend and a vanilla
JavaScript/Vite frontend.

## Repository structure

- `api/` - FastAPI entry point and client-facing endpoints.
- `agent/` - CareerCopilot agent and tools.
- `data/` and `resources/` - runtime data and architecture image.
- `CareerCopilotUI/` - frontend source, dependencies, and Vite configuration.

## Run locally

Create and activate the Python virtual environment, install the backend
dependencies, and start FastAPI from the repository root:

```bash
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000
```

In a second terminal, start the UI:

```bash
cd CareerCopilotUI
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite serves the UI locally and proxies `/api`
requests to `http://127.0.0.1:8000`.

## Deploy to Vercel

Import this repository as one Vercel project and keep the project root set to
the repository root. `vercel.json` builds `CareerCopilotUI`, publishes its
`dist/` directory at `/`, and deploys `api/index.py` for `/api/*` requests.

Configure the backend environment variables in the Vercel project settings;
do not commit `.env`. At minimum, provide the Supabase, model-provider, and
default-profile values used by the backend.

The configured 300-second API duration requires a Vercel plan that permits
that duration. If the selected plan has a lower limit, Vercel will require a
lower `maxDuration` value.
