"""FastAPI application entry point."""

from fastapi import FastAPI

from .api.routes import router as api_router

app = FastAPI(
    title="Cost-Aware Model Router API",
    description="Routes AI tasks to configured models and reports cost metadata.",
    version="1.0.0",
)


@app.get("/", tags=["health"])
def root() -> dict[str, object]:
    """Give browsers a useful landing response at the API root."""
    return {
        "message": "Cost-Aware Model Router API is running.",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "run_request": "POST /api/v1/requests",
            "routing_logs": "GET /api/v1/dashboard/logs",
        },
    }


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
