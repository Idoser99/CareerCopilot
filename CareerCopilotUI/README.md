# CareerCopilot UI

A lightweight browser interface for the CareerCopilot FastAPI service. It uses
vanilla JavaScript, CSS, and Vite; there is no frontend framework.

## Run locally

Start the CareerCopilot API on `http://127.0.0.1:8000`, then run:

```bash
npm install
npm run dev
```

Open the URL printed by Vite. During development, requests under `/api` are
proxied to the FastAPI service.

If your API uses another local address, set `CAREER_COPILOT_API_TARGET` when
starting Vite.

To explore the full UI without running FastAPI, use the development-only mock:

```bash
npm run dev:mock
```

## Build

```bash
npm run build
```

The static production files are written to `dist/`. Set
`VITE_API_BASE_URL` when building if the API is hosted under a different base
URL; otherwise the UI uses `/api` on the current host.

## CV files

PDF, DOCX, and plain-text files are parsed in the browser. Only the extracted
text is sent to `POST /api/profile/cv`; the original file is never uploaded or
stored by this UI.
