# Cost-Aware Multi-Model Router

A full-stack AI application that routes classification, extraction, summarisation, and question-answering requests through a FastAPI backend. It tries a lower-cost model first for suitable tasks and escalates to a stronger model when task complexity or the fast model's result requires it.

The Streamlit frontend lets users submit requests and explore routing, token, cost, and savings analytics. Costs are estimates calculated from the prices configured for the selected models.

## Features

- Four supported task types: classification, extraction, summarisation, and question answering.
- Complexity-aware routing and confidence-based escalation.
- FastAPI endpoints for model requests, health checks, and dashboard history.
- Streamlit interface with editable sample requests, request results, filters, dashboard views, and CSV export.
- Token-based estimated cost and savings calculations, including both calls when a request escalates.
- CSV request history that stores request metadata and input length, not the original user text.
- Separate offline strategy evaluation using a local dataset.

## Architecture

```text
Browser
  │
  ▼
Streamlit frontend (frontend/app.py)
  │  HTTP: POST /api/v1/requests
  │  HTTP: GET  /api/v1/dashboard/logs
  ▼
FastAPI backend (backend/app/main.py)
  ├─ Validate request and build task prompt
  ├─ Detect complexity and evaluate fast-model confidence
  ├─ Route to the fast model or escalate to the strong model
  ├─ Calculate token costs and strong-model baseline savings
  └─ Log request metadata to CSV
```

The frontend communicates with FastAPI over HTTP. Provider credentials and model-routing logic stay in the backend process.

## Project structure

```text
cost-aware-model-router/
├── backend/
│   └── app/
│       ├── api/             # FastAPI routes
│       ├── core/            # Provider client, router, prompts, costing, logging
│       ├── evaluation/      # Offline strategy evaluation
│       ├── services/        # Request orchestration
│       ├── main.py          # FastAPI application
│       └── schemas.py       # Request validation
├── frontend/
│   └── app.py               # Streamlit interface and dashboard
├── data/
│   ├── test_dataset.json    # Offline evaluation input
│   └── routing_logs.csv    # Generated request metadata, when requests run
├── docs/
│   ├── architecture.md
│   └── project-guide.md
├── tests/                   # Core unit tests
├── .env.example             # Safe environment-variable template
└── requirements.txt
```

## Requirements

- Python 3.10 or newer
- A provider API key for live model requests
- Internet access to the configured model provider

## Setup on Windows

Run these commands from the project root in PowerShell:

```powershell
python -m venv venv-cost-aware
.\venv-cost-aware\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `CHAT_API_KEY`. Confirm the base URL and model IDs are available for your provider. Keep `.env` private; it is excluded from Git.

### Environment variables

| Variable | Purpose |
| --- | --- |
| `CHAT_API_KEY` | Provider API credential. |
| `CHAT_BASE_URL` | Provider API origin. |
| `FAST_MODEL_ID` | Lower-cost model tried first for requests below the complexity threshold. |
| `STRONG_MODEL_ID` | Model for complex requests or escalation. |
| `CONFIDENCE_THRESHOLD` | Minimum fast-model confidence before escalation. |
| `COMPLEXITY_THRESHOLD` | Complexity score at which the strong model is called directly. |
| `MAX_OUTPUT_TOKENS` | Maximum output tokens requested per model call. |
| `FAST_INPUT_PRICE_PER_MTOK`, `FAST_OUTPUT_PRICE_PER_MTOK` | Fast-model prices in USD per million tokens. |
| `STRONG_INPUT_PRICE_PER_MTOK`, `STRONG_OUTPUT_PRICE_PER_MTOK` | Strong-model prices in USD per million tokens. |
| `LONG_INPUT_THRESHOLD`, `VERY_LONG_INPUT_THRESHOLD` | Input length thresholds used in complexity scoring. |
| `LONG_QA_CONTEXT_THRESHOLD`, `LONG_SUMMARISATION_THRESHOLD` | Task-specific long-context thresholds. |
| `ROUTER_API_URL` | Optional frontend setting for the FastAPI base URL; defaults to `http://127.0.0.1:8001`. |

The values in `.env.example` are sample configuration. Update model IDs and prices to match your provider.

## Run the application

Start the backend in the first PowerShell terminal:

```powershell
cd "D:\vs code\Drf_project\cost-aware-model-router"
.\venv-cost-aware\Scripts\Activate.ps1
uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

Start the frontend in a second terminal:

```powershell
cd "D:\vs code\Drf_project\cost-aware-model-router"
.\venv-cost-aware\Scripts\Activate.ps1
streamlit run frontend/app.py
```

Open the UI at [http://localhost:8501](http://localhost:8501).

## Using the application

1. Open **Run request** in the left navigation.
2. Select a **Task type**.
3. Optionally select **Try a sample request** to prefill an editable example.
4. Enter the input and any task-specific fields, then select **Run request**.
5. Review the answer, routing decision, token counts, estimated cost, baseline, and savings.
6. Open **Analytics dashboard** to explore Overview, Costs, and Requests. Use the filters and search to narrow the history; the Requests view can export filtered rows to CSV.

Classification expects allowed categories. Extraction expects field names. Question answering expects both a context and a question.

## API

The interactive API documentation is available at [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs) while the backend is running.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | API landing response. |
| `GET` | `/api/health` | Backend health check. |
| `POST` | `/api/v1/requests` | Submit a task for model routing. |
| `GET` | `/api/v1/dashboard/logs` | Read request metadata for the dashboard. |

Example classification payload:

```json
{
  "task_type": "classification",
  "input_text": "I was charged twice for the same invoice.",
  "categories": ["billing", "technical", "account", "general"]
}
```

The request endpoint returns an answer, initial and final model, confidence and complexity values, escalation status, token usage, and cost analysis fields.

## Cost calculation

Configured model prices are USD per million tokens:

```text
estimated cost = (input tokens × input price + output tokens × output price) / 1,000,000
estimated savings = strong-model baseline − router estimated cost
savings percentage = estimated savings / strong-model baseline × 100
```

If a request escalates, router cost includes both model calls. Prices must be kept current in `.env`. The figures are estimates from configured prices, not provider billing data.

## Offline evaluation and tests

Run the strategy evaluation from the project root:

```powershell
python -m backend.app.evaluation.evaluator
```

It compares fast-only, strong-only, and cost-aware routing strategies using `data/test_dataset.json`, then writes `data/evaluation_results.csv`.

The test suite uses pytest. If pytest is not installed in the active environment:

```powershell
python -m pip install pytest
python -m pytest
```

Live model requests may incur provider charges. The offline evaluator and unit tests serve different purposes from live API requests.

## Data and privacy

Request history is stored locally in `data/routing_logs.csv`. The logger records fields such as task type, input length, model names, token counts, costs, confidence, and escalation reason. It does not write the original user input to this CSV. Protect `.env` and avoid sharing provider credentials in screenshots, logs, or commits.

## Troubleshooting

- **Backend unavailable in the UI:** start FastAPI on port `8001` and open `http://127.0.0.1:8001/api/health` to check it.
- **FastAPI reports a missing package:** activate `venv-cost-aware` and run `pip install -r requirements.txt` in that environment.
- **Provider request fails:** check `CHAT_API_KEY`, `CHAT_BASE_URL`, model IDs, internet access, and provider API compatibility. Never print or share the API key while debugging.
- **Unexpected cost figures:** verify all four model price values in `.env` against the provider's current pricing.
- **Old entries remain in the dashboard:** analytics reads the persistent `data/routing_logs.csv` file.
- **Windows DLL errors in charts/dataframes:** the dashboard uses dependency-light rendering to avoid the affected binary chart/dataframe packages.

## More documentation

- [Detailed project guide](docs/project-guide.md)
- [Architecture notes](docs/architecture.md)
