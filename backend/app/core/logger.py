import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4


# =========================================================
# File Configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "routing_logs.csv"
_LOG_LOCK = Lock()


# =========================================================
# CSV Schema
# =========================================================

LOG_FIELDS = [
    "request_id",
    "timestamp",
    "task_type",
    "input_length",
    "complexity_score",
    "complexity_reasons",
    "initial_model",
    "final_model",
    "haiku_confidence",
    "confidence_source",
    "routing_decision",
    "routing_reason",
    "escalated",
    "escalation_reason",
    "input_tokens",
    "output_tokens",
    "actual_cost",
    "sonnet_baseline_cost",
    "savings",
    "savings_percentage",
    "latency_ms",
    "request_status",
]


# =========================================================
# Directory and File Setup
# =========================================================

def ensure_log_file() -> None:
    """
    Create the data directory and CSV file if they do not exist.
    """

    try:
        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not LOG_FILE.exists():
            with LOG_FILE.open(
                mode="w",
                newline="",
                encoding="utf-8",
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=LOG_FIELDS,
                )

                writer.writeheader()
            return

        # Extend logs created by earlier versions without dropping history.
        with LOG_FILE.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            existing_fields = reader.fieldnames or []
            if existing_fields == LOG_FIELDS:
                return
            old_rows = list(reader)

        temp_file = LOG_FILE.with_suffix(".csv.tmp")
        with temp_file.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
            writer.writeheader()
            for old_row in old_rows:
                writer.writerow({field: old_row.get(field, "") for field in LOG_FIELDS})
        os.replace(temp_file, LOG_FILE)

    except OSError as error:
        raise RuntimeError(
            f"Unable to initialize routing log file: {error}"
        ) from error


# =========================================================
# Request ID
# =========================================================

def generate_request_id() -> str:
    """
    Generate a unique request ID.
    """

    return str(uuid4())


# =========================================================
# Timestamp
# =========================================================

def generate_timestamp() -> str:
    """
    Generate a UTC timestamp in ISO 8601 format.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# Request Logger
# =========================================================

def log_request(
    task_type: str,
    input_length: int,
    complexity_score: float,
    complexity_reasons: list[str],
    initial_model: str,
    final_model: str,
    haiku_confidence: float | None,
    escalated: bool,
    escalation_reason: str,
    input_tokens: int | None,
    output_tokens: int | None,
    actual_cost: float | None,
    sonnet_baseline_cost: float | None,
    savings: float | None,
    savings_percentage: float | None,
    confidence_source: str | None = None,
    routing_decision: str = "unknown",
    routing_reason: str = "",
    latency_ms: float | None = None,
    request_status: str = "success",
    request_id: str | None = None,
    timestamp: str | None = None,
) -> bool:
    """
    Append one completed request to routing_logs.csv.

    Returns:
        True  -> log successfully written
        False -> logging failed safely
    """

    try:
        if request_id is None:
            request_id = generate_request_id()

        if timestamp is None:
            timestamp = generate_timestamp()

        # Do not store the actual user input.
        # Only the input length is recorded.

        row = {
            "request_id": request_id,
            "timestamp": timestamp,
            "task_type": task_type,
            "input_length": input_length,
            "complexity_score": complexity_score,
            "complexity_reasons": " | ".join(
                complexity_reasons
            ),
            "initial_model": initial_model,
            "final_model": final_model,
            "haiku_confidence": (
                ""
                if haiku_confidence is None
                else haiku_confidence
            ),
            "confidence_source": confidence_source or "",
            "routing_decision": routing_decision,
            "routing_reason": routing_reason,
            "escalated": escalated,
            "escalation_reason": escalation_reason,
            "input_tokens": "" if input_tokens is None else input_tokens,
            "output_tokens": "" if output_tokens is None else output_tokens,
            "actual_cost": "" if actual_cost is None else actual_cost,
            "sonnet_baseline_cost": "" if sonnet_baseline_cost is None else sonnet_baseline_cost,
            "savings": "" if savings is None else savings,
            "savings_percentage": "" if savings_percentage is None else savings_percentage,
            "latency_ms": "" if latency_ms is None else latency_ms,
            "request_status": request_status,
        }

        with _LOG_LOCK:
            ensure_log_file()
            with LOG_FILE.open(
                mode="a",
                newline="",
                encoding="utf-8",
            ) as file:
                writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
                writer.writerow(row)

        return True

    except (OSError, RuntimeError, csv.Error, ValueError, TypeError) as error:
        print(
            f"WARNING: Failed to write routing log: {error}"
        )

        return False
