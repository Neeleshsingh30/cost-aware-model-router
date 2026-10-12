# Cost-Aware Multi-Model Router — Project Guide

## 1. Project overview

The Cost-Aware Multi-Model Router is a small full-stack AI application. A user submits a classification, extraction, summarisation, or question-answering task through a Streamlit interface. A FastAPI backend builds the task prompt, assesses complexity, and routes the work to a configured lower-cost model or, when needed, a stronger model.

The goal is to reduce estimated model spend while still returning usable answers. The router uses model confidence and task complexity to decide when escalation is appropriate. It also reports token use, estimated costs, and savings compared with the configured strong-model baseline.

## 2. Main components

| Component | Responsibility |
| --- | --- |
| `frontend/app.py` | Streamlit user interface, sample requests, result display, analytics filters and CSV export. It calls FastAPI over HTTP. |
| `backend/app/main.py` | Creates the FastAPI application and exposes the root and health endpoints. |
| `backend/app/api/routes.py` | Defines the request and dashboard-log API routes. |
| `backend/app/schemas.py` | Validates incoming request fields and task names. |
| `backend/app/services/request_service.py` | Connects prompt construction, routing, cost analysis, and request logging. |
| `backend/app/core/prompt_builder.py` | Creates task-specific instructions for the four supported tasks. |
| `backend/app/core/complexity_detector.py` | Scores task complexity and records reasons for the score. |
| `backend/app/core/confidence_evaluator.py` | Evaluates whether the fast-model answer is sufficiently confident and valid. |
| `backend/app/core/router.py` | Selects the model, handles escalation, aggregates token usage, and calculates request cost. |
| `backend/app/core/claude_client.py` | Sends model requests to the configured provider and normalizes responses and errors. |
| `backend/app/core/cost_tracker.py` | Calculates estimated costs from token counts and configured per-model prices. |
| `backend/app/core/logger.py` | Appends request metadata to `data/routing_logs.csv`. |
| `backend/app/evaluation/evaluator.py` | Runs a separate offline comparison using the evaluation dataset. |

## 3. Architecture and request flow

```text
Browser
  │
  ▼
Streamlit frontend (frontend/app.py)
  │  POST /api/v1/requests
  │  GET  /api/v1/dashboard/logs
  ▼
FastAPI backend (backend/app/main.py)
  │
  ├─ Validate request
  ├─ Build task-specific prompt
  ├─ Score complexity
  ├─ Route to fast model or strong model
  ├─ Evaluate fast-model answer and escalate if needed
  ├─ Calculate token costs and baseline savings
  └─ Log request metadata
```

The browser talks to Streamlit. Streamlit makes server-side HTTP requests to FastAPI. Provider credentials and model routing are handled by the backend, not by browser code.

### Routing behavior

1. The backend validates the task and builds its prompt.
2. The complexity detector scores the prompt.
3. If complexity is at or above `COMPLEXITY_THRESHOLD`, the request goes directly to the strong model.
4. Otherwise, the fast model is tried first.
5. If the fast result is invalid or its confidence is below `CONFIDENCE_THRESHOLD`, the router tries the strong model.
6. The router totals token use and cost across both calls if escalation occurred.
7. The service calculates a strong-model baseline and estimated savings, then writes request metadata to the CSV log when cost data is available.

The exact rules are implemented in `backend/app/core/router.py`; the thresholds and prices are read from `.env`.

## 4. Supported tasks

- **Classification:** choose one label from the categories supplied with the request.
- **Extraction:** return requested fields as JSON; missing information should be `null`.
- **Summarisation:** produce a concise summary grounded in the supplied text.
- **Question and answer:** answer using the supplied context and state when the context is insufficient.

The Streamlit sample selector fills the form with an editable example. It is optional; users can enter their own input.

## 5. Local setup (Windows PowerShell)

Open a PowerShell terminal in the project root:

```powershell
cd "D:\vs code\Drf_project\cost-aware-model-router"
python -m venv venv-cost-aware
.\venv-cost-aware\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a valid provider API key. Keep this file private and never commit it.

Start the backend in the first terminal:

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

Start the frontend in a second terminal, with the same environment activated:

```powershell
cd "D:\vs code\Drf_project\cost-aware-model-router"
.\venv-cost-aware\Scripts\Activate.ps1
streamlit run frontend/app.py
```

Open `http://localhost:8501` in a browser. The frontend expects FastAPI at `http://127.0.0.1:8001` by default. To use another backend URL, set `ROUTER_API_URL` before starting Streamlit.

## 6. Environment configuration

| Variable | Meaning |
| --- | --- |
| `CHAT_API_KEY` | Provider API key. Keep secret. |
| `CHAT_BASE_URL` | Provider API origin, for example `https://api.experientiallabs.ai`. |
| `FAST_MODEL_ID` | Model tried first for requests below the complexity threshold. |
| `STRONG_MODEL_ID` | Model used for direct complex requests or escalation. |
| `CONFIDENCE_THRESHOLD` | Minimum fast-model confidence before escalation. |
| `COMPLEXITY_THRESHOLD` | Complexity score at or above which the strong model is called directly. |
| `MAX_OUTPUT_TOKENS` | Maximum response tokens requested from a model. |
| `FAST_INPUT_PRICE_PER_MTOK` / `FAST_OUTPUT_PRICE_PER_MTOK` | Fast-model input/output prices in USD per million tokens. |
| `STRONG_INPUT_PRICE_PER_MTOK` / `STRONG_OUTPUT_PRICE_PER_MTOK` | Strong-model input/output prices in USD per million tokens. |
| `LONG_INPUT_THRESHOLD`, `VERY_LONG_INPUT_THRESHOLD` | Text-length thresholds used by complexity scoring. |
| `LONG_QA_CONTEXT_THRESHOLD`, `LONG_SUMMARISATION_THRESHOLD` | Task-specific long-context thresholds. |
| `ROUTER_API_URL` | Optional frontend setting for the FastAPI base URL. |

Pricing in `.env.example` is illustrative configuration. Confirm and update it to match the provider and model prices you actually use.

## 7. API reference

FastAPI's interactive API docs are available at `http://127.0.0.1:8001/docs`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | API landing response with endpoint links. |
| `GET` | `/api/health` | Basic backend health check. |
| `POST` | `/api/v1/requests` | Submit a request for model routing. |
| `GET` | `/api/v1/dashboard/logs` | Fetch logged request metadata for analytics. |

Example classification request:

```json
{
  "task_type": "classification",
  "input_text": "I was charged twice for the same invoice.",
  "categories": ["billing", "technical", "account", "general"]
}
```

The response includes the answer, initial and final model, confidence, complexity score, escalation status, token counts, estimated actual cost, strong-model baseline, savings, and any error information.

## 8. Cost and savings calculations

Prices are configured in USD per million tokens. For a model call:

```text
estimated cost = input tokens / 1,000,000 × input price
               + output tokens / 1,000,000 × output price
```

If the router escalates, the reported actual cost includes the fast-model call and the strong-model call. The baseline estimates the same combined input/output token usage at the configured strong-model prices.

```text
estimated savings = strong-model baseline − router estimated cost
savings percentage = estimated savings / strong-model baseline × 100
```

These values are estimates based on local configuration; they are not fetched from a provider's billing account. Keep configured model prices current for useful comparisons.

## 9. Analytics dashboard

The dashboard loads metadata from `GET /api/v1/dashboard/logs` and provides:

- **Overview:** request totals, success rate, fast-model share, escalations, cost/savings indicators, and request/task/outcome charts.
- **Costs:** estimated router spend versus always using the strong model, plus cumulative savings over time.
- **Requests:** searchable request details and a CSV download of the filtered history.
- **Filters:** final model, task type, escalated-only, and routing-reason/model search.

The log stores request metadata and input length, not the original user input. The dashboard depends on the backend being available and on its CSV log file being readable.

## 10. Evaluation and tests

Run the offline strategy evaluation from the project root:

```powershell
python -m backend.app.evaluation.evaluator
```

It uses `data/test_dataset.json` and writes evaluation output to `data/evaluation_results.csv` (as described in the project README). This evaluation is separate from live Streamlit requests.

Run the unit tests with:

```powershell
python -m pip install pytest
python -m pytest
```

Live requests call the configured model provider and may incur usage charges. Unit tests and offline evaluation are the safer place to check local routing logic before sending production prompts.

## 11. Troubleshooting

- **FastAPI import or dependency error:** activate the project virtual environment and install `requirements.txt` there.
- **Streamlit says backend is unavailable:** confirm the API is running on port `8001`, then check `http://127.0.0.1:8001/api/health`.
- **Provider connection/authentication failure:** check `CHAT_BASE_URL`, `CHAT_API_KEY`, internet access, and provider API compatibility. Do not paste the secret key into logs or messages.
- **Unexpected cost values:** verify all four per-million-token prices in `.env` match the configured models and provider pricing.
- **Old analytics remain visible:** the dashboard reads persistent rows from `data/routing_logs.csv`; historical requests remain until that file is archived or cleared.
- **Streamlit chart DLL failures on Windows:** use the project's dependency-light dashboard rendering and avoid reintroducing dataframe/chart calls that import blocked binary dependencies.

## 12. Important files and generated data

- `.env.example` — safe configuration template; copy to `.env` and add the secret locally.
- `data/test_dataset.json` — offline evaluation inputs.
- `data/evaluation_results.csv` — generated offline evaluation results.
- `data/routing_logs.csv` — persistent routing and cost metadata for the dashboard.
- `docs/architecture.md` — concise architecture summary.
- `frontend/app.py` — Streamlit UI.
- `backend/app/` — FastAPI application, routing logic, and services.
