import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


# =========================================================
# File Configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "routing_logs.csv"


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
    "escalated",
    "escalation_reason",
    "input_tokens",
    "output_tokens",
    "actual_cost",
    "sonnet_baseline_cost",
    "savings",
    "savings_percentage",
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
    input_tokens: int,
    output_tokens: int,
    actual_cost: float,
    sonnet_baseline_cost: float,
    savings: float,
    savings_percentage: float,
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
        ensure_log_file()

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
            "escalated": escalated,
            "escalation_reason": escalation_reason,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "actual_cost": actual_cost,
            "sonnet_baseline_cost": sonnet_baseline_cost,
            "savings": savings,
            "savings_percentage": savings_percentage,
        }

        with LOG_FILE.open(
            mode="a",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=LOG_FIELDS,
            )

            writer.writerow(row)

        return True

    except (OSError, csv.Error, ValueError, TypeError) as error:
        print(
            f"WARNING: Failed to write routing log: {error}"
        )

        return False