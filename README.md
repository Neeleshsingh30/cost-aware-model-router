# Cost-Aware Multi-Model Router

A small full-stack app that routes classification, extraction, summarisation, and Q&A requests to a lower-cost model first, escalating to a stronger model when complexity or confidence rules require it.

## Project layout

- `backend/app/main.py`: FastAPI application entry point.
- `backend/app/api/`: request and dashboard HTTP endpoints.
- `backend/app/core/`: model client, routing, prompts, complexity checks, costing, and logging.
- `backend/app/evaluation/`: offline strategy evaluation command.
- `frontend/app.py`: Streamlit UI. It calls the backend over HTTP and contains no model credentials or routing logic.
- `data/`: evaluation dataset, saved evaluation output, and generated request logs.
- `tests/`: unit tests for core modules.

## Setup

Use Python 3.10 or newer. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set the provider API key and model IDs in `.env`. Keep `.env` private; it is excluded from Git.

## Run locally

Start the API in one terminal:

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

Start the frontend in another terminal:

```powershell
streamlit run frontend/app.py
```

The frontend defaults to `http://127.0.0.1:8001`. Set `ROUTER_API_URL` if the API runs elsewhere. API documentation is available at `http://127.0.0.1:8001/docs`; health check is `GET /api/health`.

## API endpoints

- `POST /api/v1/requests` — run a task through the model router.
- `GET /api/v1/dashboard/logs` — return request metadata for the dashboard. User input text is not stored.

## Evaluation

From the project directory, run:

```powershell
python -m backend.app.evaluation.evaluator
```

This compares fast-only, strong-only, and routed strategies using `data/test_dataset.json`, then writes results to `data/evaluation_results.csv`.
