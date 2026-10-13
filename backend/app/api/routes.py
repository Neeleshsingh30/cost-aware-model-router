"""HTTP endpoints that expose model routing to the frontend."""

import csv
import logging

from fastapi import APIRouter, HTTPException

from ..core.logger import LOG_FILE
from ..schemas import RequestPayload
from ..services.request_service import process_request

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)


@router.post("/requests")
def create_request(payload: RequestPayload) -> dict:
    """Build a task prompt, route it to a model, and log its costs."""
    try:
        return process_request(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Request processing failed")
        raise HTTPException(
            status_code=502,
            detail="Request could not be processed. Check the backend logs.",
        ) from error


@router.get("/dashboard/logs")
def get_dashboard_logs() -> list[dict[str, str]]:
    """Return routing metadata for the dashboard; user input is never logged."""
    if not LOG_FILE.exists():
        return []
    try:
        with LOG_FILE.open("r", newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))
    except (OSError, csv.Error) as error:
        raise HTTPException(status_code=500, detail="Could not read routing logs.") from error
