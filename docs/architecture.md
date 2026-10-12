# Architecture

The project has a Streamlit presentation layer and a FastAPI application layer. The frontend communicates with the backend over HTTP; provider credentials and model routing stay in the backend process.

```text
Browser
  │
  ▼
Streamlit UI (frontend/app.py)
  │  POST /api/v1/requests
  │  GET  /api/v1/dashboard/logs
  ▼
FastAPI (backend/app/main.py)
  ├── API routes and request schemas
  ├── Request service
  └── Core services
      ├── task prompt builder
      ├── complexity and confidence evaluation
      ├── fast/strong model router
      ├── token cost calculator
      └── CSV request logger
```

## Request lifecycle

1. The UI sends a task type, input, and any task-specific fields to the API.
2. FastAPI validates the payload and the request service builds the prompt.
3. The router evaluates complexity. It calls the strong model directly for complex requests; otherwise it tries the fast model and escalates when confidence or response validation requires it.
4. The service calculates the strong-model baseline and estimated savings, then records request metadata in `data/routing_logs.csv`.
5. FastAPI returns the answer and routing/cost details to Streamlit.

The logger stores input length and routing metadata, not the input text itself. The evaluation script is separate from the live API and uses `data/test_dataset.json`.
