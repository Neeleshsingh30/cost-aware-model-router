"""
Stage 12 + Stage 13: Evaluation Engine
Cost-Aware Multi-Model Router

Evaluates the held-out test_dataset.json with three strategies:

    A. Always Fast Model
       deepseek-v4-flash

    B. Always Strong Model
       gpt-6-sol

    C. Cost-Aware Router

Results are saved to:

    data/evaluation_results.csv

The CSV contains:

    1. Overall strategy results
    2. Per-task strategy results

Evaluation notes:

- Classification uses exact normalized category matching.
- Extraction uses normalized field-level matching.
- Summarisation and Q&A use deterministic token-level F1.
- Token-level F1 is not a semantic judge.
- Costs are estimates based on configured model pricing.
- Failed API calls are recorded as failed cases.
- Failed cases remain visible in request/cost statistics.
- No evaluation results are fabricated.
"""


from __future__ import annotations


import csv
import json
import re
import sys

from collections import Counter
from pathlib import Path
from typing import Any


from claude_client import call_model
from cost_tracker import calculate_cost
from prompt_builder import build_prompt
from router import route_request


try:

    from config import (
        FAST_MODEL_ID,
        STRONG_MODEL_ID,
    )

except ImportError:

    from claude_client import (
        FAST_MODEL as FAST_MODEL_ID,
    )

    from claude_client import (
        STRONG_MODEL as STRONG_MODEL_ID,
    )


# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = (
    BASE_DIR / "test_dataset.json"
)

DATA_DIR = (
    BASE_DIR / "data"
)

RESULTS_PATH = (
    DATA_DIR / "evaluation_results.csv"
)


# =========================================================
# Default Classification Categories
# =========================================================

DEFAULT_CATEGORIES = [
    "billing",
    "technical",
    "account",
    "general",
]


# =========================================================
# Strategy Names
# =========================================================

STRATEGY_FAST = (
    "Always Fast Model"
)

STRATEGY_STRONG = (
    "Always Strong Model"
)

STRATEGY_ROUTER = (
    "Cost-Aware Router"
)


STRATEGIES = [
    STRATEGY_FAST,
    STRATEGY_STRONG,
    STRATEGY_ROUTER,
]


# =========================================================
# Task Types
# =========================================================

TASK_TYPES = [
    "classification",
    "extraction",
    "summarisation",
    "qa",
]


# =========================================================
# Result CSV Columns
# =========================================================

RESULT_COLUMNS = [
    "level",
    "strategy",
    "task_type",
    "total_requests",
    "successful_requests",
    "failed_requests",
    "accuracy",
    "total_cost",
    "average_cost_per_request",
    "fast_model_calls",
    "strong_model_calls",
    "escalations",
    "savings_vs_always_strong",
    "savings_percentage_vs_always_strong",
]


# =========================================================
# Case-Level Columns
# =========================================================

CASE_COLUMNS = [
    "strategy",
    "case_id",
    "task_type",
    "score",
    "correct",
    "model",
    "initial_model",
    "final_model",
    "input_tokens",
    "output_tokens",
    "cost",
    "error",
    "escalated",
]


# =========================================================
# Dataset Loading
# =========================================================

def load_dataset(
    path: Path = DATASET_PATH,
) -> list[dict[str, Any]]:
    """
    Load and validate the held-out evaluation dataset.
    """

    if not path.exists():

        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(data, list):

        raise ValueError(
            "test_dataset.json must contain "
            "a JSON list."
        )

    required = {
        "id",
        "task_type",
        "input",
        "expected_output",
        "evaluation_criteria",
    }

    for index, item in enumerate(
        data,
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):

            raise ValueError(
                f"Dataset item {index} "
                "is not a JSON object."
            )

        missing = (
            required - item.keys()
        )

        if missing:

            raise ValueError(
                f"Dataset item {index} "
                f"is missing fields: "
                f"{sorted(missing)}"
            )

    return data


# =========================================================
# Text Normalization
# =========================================================

def normalize_text(
    value: Any,
) -> str:
    """
    Normalize text for deterministic comparison.
    """

    if value is None:

        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip().lower(),
    )


# =========================================================
# Tokenization
# =========================================================

def normalize_tokens(
    value: Any,
) -> list[str]:
    """
    Tokenize normalized text using a simple
    deterministic tokenizer.
    """

    text = normalize_text(
        value
    )

    return re.findall(
        r"[a-z0-9]+(?:['’-][a-z0-9]+)?",
        text,
    )


# =========================================================
# Token F1
# =========================================================

def token_f1(
    reference: Any,
    prediction: Any,
) -> float:
    """
    Calculate token-level F1.

    Used for:
        - Summarisation
        - Q&A

    This is a deterministic lexical metric,
    not a semantic evaluation.
    """

    reference_tokens = normalize_tokens(
        reference
    )

    prediction_tokens = normalize_tokens(
        prediction
    )

    if (
        not reference_tokens
        and not prediction_tokens
    ):

        return 1.0

    if (
        not reference_tokens
        or not prediction_tokens
    ):

        return 0.0

    reference_counts = Counter(
        reference_tokens
    )

    prediction_counts = Counter(
        prediction_tokens
    )

    overlap = sum(
        (
            reference_counts
            & prediction_counts
        ).values()
    )

    if overlap == 0:

        return 0.0

    precision = (
        overlap
        / len(prediction_tokens)
    )

    recall = (
        overlap
        / len(reference_tokens)
    )

    return round(
        (
            2
            * precision
            * recall
            / (precision + recall)
        ),
        4,
    )


# =========================================================
# Structured Normalization
# =========================================================

def normalize_structured(
    value: Any,
) -> Any:
    """
    Normalize nested extraction values.
    """

    if isinstance(
        value,
        dict,
    ):

        return {
            str(key).strip().lower():
            normalize_structured(val)
            for key, val in value.items()
        }

    if isinstance(
        value,
        list,
    ):

        return [
            normalize_structured(item)
            for item in value
        ]

    if isinstance(
        value,
        str,
    ):

        return normalize_text(
            value
        )

    return value


# =========================================================
# Structured Comparison
# =========================================================

def structured_value_equal(
    expected: Any,
    actual: Any,
) -> bool:
    """
    Compare extraction values recursively
    after normalization.
    """

    if expected is None:

        return (
            actual is None
            or normalize_text(actual)
            in {
                "",
                "null",
                "none",
            }
        )

    if isinstance(
        expected,
        dict,
    ):

        if not isinstance(
            actual,
            dict,
        ):

            return False

        for (
            key,
            expected_value,
        ) in expected.items():

            if key not in actual:

                return False

            if not structured_value_equal(
                expected_value,
                actual[key],
            ):

                return False

        return True

    if isinstance(
        expected,
        list,
    ):

        if not isinstance(
            actual,
            list,
        ):

            return False

        if len(expected) != len(actual):

            return False

        return all(
            structured_value_equal(
                expected_item,
                actual_item,
            )
            for (
                expected_item,
                actual_item,
            ) in zip(
                expected,
                actual,
            )
        )

    if (
        isinstance(
            expected,
            (int, float),
        )
        and isinstance(
            actual,
            (int, float),
        )
    ):

        return expected == actual

    return (
        normalize_text(expected)
        == normalize_text(actual)
    )


# =========================================================
# Extraction Score
# =========================================================

def extraction_score(
    expected: dict[str, Any],
    actual: Any,
) -> float:
    """
    Return fraction of required extraction
    fields that matched.
    """

    if not expected:

        return (
            1.0
            if actual == {}
            else 0.0
        )

    if not isinstance(
        actual,
        dict,
    ):

        return 0.0

    matched = 0

    for (
        key,
        expected_value,
    ) in expected.items():

        if (
            key in actual
            and structured_value_equal(
                expected_value,
                actual[key],
            )
        ):

            matched += 1

    return round(
        matched / len(expected),
        4,
    )


# =========================================================
# JSON Parser
# =========================================================

def parse_json_answer(
    text: str,
) -> Any:
    """
    Parse model JSON response.

    Supports responses with Markdown
    code fences.
    """

    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    try:

        return json.loads(
            cleaned
        )

    except json.JSONDecodeError:

        match = re.search(
            r"\{.*\}",
            cleaned,
            re.DOTALL,
        )

        if match:

            return json.loads(
                match.group(0)
            )

        raise


# =========================================================
# Classification Categories
# =========================================================

def get_categories(
    case: dict[str, Any],
) -> list[str]:
    """
    Return classification categories.
    """

    categories = case.get(
        "categories"
    )

    if categories:

        return [
            str(item)
            for item in categories
        ]

    return DEFAULT_CATEGORIES


# =========================================================
# Extraction Fields
# =========================================================

def get_fields(
    case: dict[str, Any],
) -> list[str]:
    """
    Return extraction fields.
    """

    fields = case.get(
        "fields"
    )

    if fields:

        return [
            str(item)
            for item in fields
        ]

    expected = case[
        "expected_output"
    ]

    if isinstance(
        expected,
        dict,
    ):

        return list(
            expected.keys()
        )

    raise ValueError(
        f"Extraction case "
        f"{case['id']} requires "
        "expected_output to be an object."
    )


# =========================================================
# Q&A Question
# =========================================================

def get_qa_question(
    case: dict[str, Any],
) -> str:
    """
    Return the Q&A question.

    The evaluator refuses to invent a question.
    """

    question = case.get(
        "question"
    )

    if (
        not question
        or not str(question).strip()
    ):

        raise ValueError(
            f"Q&A case {case['id']} "
            "is missing a 'question' field. "
            "The evaluator will not invent "
            "questions."
        )

    return str(
        question
    )


# =========================================================
# Build Prompt
# =========================================================

def build_case_prompt(
    case: dict[str, Any],
) -> str:
    """
    Build the normal task prompt for
    standalone model baselines.
    """

    task_type = (
        case["task_type"]
        .lower()
        .strip()
    )

    if task_type == "classification":

        return build_prompt(
            task_type=task_type,
            input_text=case["input"],
            categories=get_categories(
                case
            ),
        )

    if task_type == "extraction":

        return build_prompt(
            task_type=task_type,
            input_text=case["input"],
            fields=get_fields(
                case
            ),
        )

    if task_type == "summarisation":

        return build_prompt(
            task_type=task_type,
            input_text=case["input"],
        )

    if task_type == "qa":

        return build_prompt(
            task_type=task_type,
            input_text=case["input"],
            question=get_qa_question(
                case
            ),
        )

    raise ValueError(
        f"Unsupported task_type: "
        f"{case['task_type']}"
    )


# =========================================================
# Evaluate Answer
# =========================================================

def evaluate_answer(
    case: dict[str, Any],
    answer: Any,
) -> tuple[float, bool]:
    """
    Evaluate one model answer according
    to the task type.
    """

    task_type = (
        case["task_type"]
        .lower()
        .strip()
    )

    expected = case[
        "expected_output"
    ]

    # -----------------------------------------------------
    # Classification
    # -----------------------------------------------------

    if task_type == "classification":

        score = float(
            normalize_text(
                answer
            )
            == normalize_text(
                expected
            )
        )

        return (
            score,
            score == 1.0,
        )

    # -----------------------------------------------------
    # Extraction
    # -----------------------------------------------------

    if task_type == "extraction":

        score = extraction_score(
            expected,
            answer,
        )

        return (
            score,
            score == 1.0,
        )

    # -----------------------------------------------------
    # Summarisation / Q&A
    # -----------------------------------------------------

    if task_type in {
        "summarisation",
        "qa",
    }:

        score = token_f1(
            expected,
            answer,
        )

        return (
            score,
            score >= 0.50,
        )

    raise ValueError(
        f"Unsupported task_type: "
        f"{case['task_type']}"
    )


# =========================================================
# Model Key
# =========================================================

def model_key(
    model: str,
) -> str:
    """
    Map actual model ID to the cost_tracker
    fast/strong keys.
    """

    model_lower = model.lower()

    if (
        model == FAST_MODEL_ID
        or "deepseek" in model_lower
    ):

        return "fast"

    if (
        model == STRONG_MODEL_ID
        or "gpt" in model_lower
    ):

        return "strong"

    raise ValueError(
        f"Unknown model for cost calculation: "
        f"{model}"
    )


# =========================================================
# Model Cost
# =========================================================

def model_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate model cost using configured
    fast/strong pricing.

    Convert Decimal to float so evaluator
    calculations use one numeric type.
    """

    cost = calculate_cost(
        model=model_key(model),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    return float(
        cost
    )


# =========================================================
# Baseline Evaluation
# =========================================================

def evaluate_baseline_case(
    case: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    """
    Run one case through a fixed-model baseline.
    """

    try:

        prompt = build_case_prompt(
            case
        )

    except ValueError as error:

        return {
            "score": 0.0,
            "correct": False,
            "model": model,
            "initial_model": model,
            "final_model": model,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "error": str(error),
            "escalated": False,
        }

    result = call_model(
        model=model,
        prompt=prompt,
    )

    input_tokens = result.get(
        "input_tokens",
        0,
    )

    output_tokens = result.get(
        "output_tokens",
        0,
    )

    # -----------------------------------------------------
    # API Failure
    # -----------------------------------------------------

    if result.get("error"):

        return {
            "score": 0.0,
            "correct": False,
            "model": model,
            "initial_model": model,
            "final_model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": model_cost(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
            "error": result["error"],
            "escalated": False,
        }

    raw_answer = result.get(
        "text",
        "",
    )

    answer: Any = raw_answer

    # -----------------------------------------------------
    # Extraction JSON
    # -----------------------------------------------------

    if (
        case["task_type"]
        .lower()
        == "extraction"
    ):

        try:

            answer = parse_json_answer(
                raw_answer
            )

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:

            return {
                "score": 0.0,
                "correct": False,
                "model": model,
                "initial_model": model,
                "final_model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": model_cost(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                ),
                "error": (
                    f"Invalid extraction JSON: "
                    f"{error}"
                ),
                "escalated": False,
            }

    score, correct = evaluate_answer(
        case,
        answer,
    )

    return {
        "score": score,
        "correct": correct,
        "model": model,
        "initial_model": model,
        "final_model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": model_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        "error": None,
        "escalated": False,
    }


# =========================================================
# Router Evaluation
# =========================================================

def evaluate_router_case(
    case: dict[str, Any],
) -> dict[str, Any]:
    """
    Run one case through the cost-aware router.
    """

    try:

        prompt = build_case_prompt(
            case
        )

    except ValueError as error:

        return {
            "score": 0.0,
            "correct": False,
            "model": "",
            "initial_model": "",
            "final_model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "error": str(error),
            "escalated": False,
        }

    try:

        result = route_request(
            text=prompt,
            task_type=case["task_type"],
        )

    except Exception as error:

        return {
            "score": 0.0,
            "correct": False,
            "model": "",
            "initial_model": "",
            "final_model": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "error": (
                f"Router error: {error}"
            ),
            "escalated": False,
        }

    initial_model = result.get(
        "initial_model",
        "",
    )

    final_model = result.get(
        "final_model",
        "",
    )

    answer = result.get(
        "answer",
        "",
    )

    # -----------------------------------------------------
    # Extraction JSON
    # -----------------------------------------------------

    if (
        case["task_type"]
        .lower()
        == "extraction"
    ):

        try:

            answer = parse_json_answer(
                answer
            )

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:

            return {
                "score": 0.0,
                "correct": False,
                "model": final_model,
                "initial_model": initial_model,
                "final_model": final_model,
                "input_tokens": result.get(
                    "input_tokens",
                    0,
                ),
                "output_tokens": result.get(
                    "output_tokens",
                    0,
                ),
                "cost": float(
                    result.get(
                        "actual_cost",
                        0.0,
                    )
                    or 0
                ),
                "error": (
                    f"Invalid extraction JSON: "
                    f"{error}"
                ),
                "escalated": bool(
                    result.get(
                        "escalated",
                        False,
                    )
                ),
            }

    score, correct = evaluate_answer(
        case,
        answer,
    )

    return {
        "score": score,
        "correct": correct,
        "model": final_model,
        "initial_model": initial_model,
        "final_model": final_model,
        "input_tokens": result.get(
            "input_tokens",
            0,
        ),
        "output_tokens": result.get(
            "output_tokens",
            0,
        ),
        "cost": float(
            result.get(
                "actual_cost",
                0.0,
            )
            or 0
        ),
        "error": result.get(
            "error"
        ),
        "escalated": bool(
            result.get(
                "escalated",
                False,
            )
        ),
    }


# =========================================================
# Model Call Classification
# =========================================================

def _classify_single_model(
    model: str,
) -> tuple[int, int]:
    """
    Classify one model as Fast or Strong.
    """

    if not model:

        return 0, 0

    model_lower = model.lower()

    if (
        model == FAST_MODEL_ID
        or "deepseek" in model_lower
    ):

        return 1, 0

    if (
        model == STRONG_MODEL_ID
        or "gpt" in model_lower
    ):

        return 0, 1

    return 0, 0


def classify_model_calls(
    initial_model: str,
    final_model: str,
) -> tuple[int, int]:
    """
    Count actual model calls.

    Examples:

        Fast -> Fast
            Fast = 1
            Strong = 0

        Strong -> Strong
            Fast = 0
            Strong = 1

        Fast -> Strong
            Fast = 1
            Strong = 1
    """

    fast_calls = 0
    strong_calls = 0

    initial_fast, initial_strong = (
        _classify_single_model(
            initial_model
        )
    )

    final_fast, final_strong = (
        _classify_single_model(
            final_model
        )
    )

    fast_calls += initial_fast
    strong_calls += initial_strong

    # Only count the final model separately
    # when it differs from the initial model.
    if final_model != initial_model:

        fast_calls += final_fast
        strong_calls += final_strong

    return (
        fast_calls,
        strong_calls,
    )


# =========================================================
# Strategy Summary
# =========================================================

def summarize_strategy(
    strategy: str,
    case_results: list[dict[str, Any]],
    task_type: str = "All",
) -> dict[str, Any]:
    """
    Aggregate evaluation results.

    task_type="All" creates an overall summary.

    Other task types create per-task summaries.
    """

    total_requests = len(
        case_results
    )

    successful_requests = sum(
        result.get("error") is None
        for result in case_results
    )

    failed_requests = (
        total_requests
        - successful_requests
    )

    valid_scores = [
        float(
            result["score"]
        )
        for result in case_results
        if result.get("error") is None
    ]

    accuracy = (
        sum(valid_scores)
        / len(valid_scores)
        if valid_scores
        else 0.0
    )

    total_cost = sum(
        (
            float(
                result.get(
                    "cost",
                    0.0,
                )
                or 0.0
            )
            for result in case_results
        ),
        0.0,
    )

    average_cost = (
        total_cost
        / total_requests
        if total_requests
        else 0.0
    )

    fast_calls = 0
    strong_calls = 0
    escalations = 0

    for result in case_results:

        result_fast, result_strong = (
            classify_model_calls(
                result.get(
                    "initial_model",
                    result.get(
                        "model",
                        "",
                    ),
                ),
                result.get(
                    "final_model",
                    result.get(
                        "model",
                        "",
                    ),
                ),
            )
        )

        fast_calls += result_fast
        strong_calls += result_strong

        escalations += int(
            result.get(
                "escalated",
                False,
            )
        )

    return {
        "level": (
            "overall"
            if task_type == "All"
            else "task"
        ),
        "strategy": strategy,
        "task_type": task_type,
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "accuracy": round(
            accuracy,
            4,
        ),
        "total_cost": round(
            total_cost,
            8,
        ),
        "average_cost_per_request": round(
            average_cost,
            8,
        ),
        "fast_model_calls": fast_calls,
        "strong_model_calls": strong_calls,
        "escalations": escalations,
        "savings_vs_always_strong": 0.0,
        "savings_percentage_vs_always_strong": 0.0,
    }


# =========================================================
# Apply Overall Savings
# =========================================================

def apply_savings(
    summaries: list[dict[str, Any]],
) -> None:
    """
    Calculate savings for overall strategy summaries.

    Savings are meaningful only for overall summaries.
    """

    strong_baseline = next(
        (
            item
            for item in summaries
            if (
                item["strategy"]
                == STRATEGY_STRONG
            )
            and (
                item["level"]
                == "overall"
            )
        ),
        None,
    )

    if strong_baseline is None:

        return

    strong_cost = float(
        strong_baseline[
            "total_cost"
        ]
    )

    for summary in summaries:

        if summary["level"] != "overall":

            continue

        strategy_cost = float(
            summary[
                "total_cost"
            ]
        )

        savings = round(
            strong_cost
            - strategy_cost,
            8,
        )

        summary[
            "savings_vs_always_strong"
        ] = savings

        summary[
            "savings_percentage_vs_always_strong"
        ] = (
            round(
                (
                    savings
                    / strong_cost
                )
                * 100,
                4,
            )
            if strong_cost > 0
            else 0.0
        )


# =========================================================
# Save Evaluation Results
# =========================================================

def save_evaluation_results(
    summaries: list[dict[str, Any]],
    path: Path = RESULTS_PATH,
) -> None:
    """
    Save overall and per-task strategy summaries.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=RESULT_COLUMNS,
            extrasaction="ignore",
        )

        writer.writeheader()

        writer.writerows(
            summaries
        )


# =========================================================
# Run Evaluation
# =========================================================

def run_evaluation(
    dataset_path: Path = DATASET_PATH,
    save_results: bool = True,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """
    Run all three evaluation strategies.

    Saves:

        Overall results
        +
        Per-task results
    """

    dataset = load_dataset(
        dataset_path
    )

    all_case_results: list[
        dict[str, Any]
    ] = []

    strategy_results: dict[
        str,
        list[dict[str, Any]],
    ] = {
        STRATEGY_FAST: [],
        STRATEGY_STRONG: [],
        STRATEGY_ROUTER: [],
    }

    print(
        f"Loaded {len(dataset)} "
        "held-out test cases."
    )

    print(
        f"Fast model:   "
        f"{FAST_MODEL_ID}"
    )

    print(
        f"Strong model: "
        f"{STRONG_MODEL_ID}"
    )

    print()

    # =====================================================
    # Evaluate Every Case
    # =====================================================

    for index, case in enumerate(
        dataset,
        start=1,
    ):

        print(
            f"[{index}/{len(dataset)}] "
            f"{case['id']} "
            f"({case['task_type']})"
        )

        # -------------------------------------------------
        # Strategy A: Always Fast
        # -------------------------------------------------

        fast_result = (
            evaluate_baseline_case(
                case,
                FAST_MODEL_ID,
            )
        )

        # -------------------------------------------------
        # Strategy B: Always Strong
        # -------------------------------------------------

        strong_result = (
            evaluate_baseline_case(
                case,
                STRONG_MODEL_ID,
            )
        )

        # -------------------------------------------------
        # Strategy C: Cost-Aware Router
        # -------------------------------------------------

        router_result = (
            evaluate_router_case(
                case
            )
        )

        case_runs = [
            (
                STRATEGY_FAST,
                fast_result,
            ),
            (
                STRATEGY_STRONG,
                strong_result,
            ),
            (
                STRATEGY_ROUTER,
                router_result,
            ),
        ]

        for strategy, result in case_runs:

            strategy_results[
                strategy
            ].append(result)

            all_case_results.append(
                {
                    "strategy": strategy,
                    "case_id": case["id"],
                    "task_type": case[
                        "task_type"
                    ],
                    "score": result[
                        "score"
                    ],
                    "correct": result[
                        "correct"
                    ],
                    "model": result.get(
                        "model",
                        "",
                    ),
                    "initial_model": result.get(
                        "initial_model",
                        "",
                    ),
                    "final_model": result.get(
                        "final_model",
                        "",
                    ),
                    "input_tokens": result.get(
                        "input_tokens",
                        0,
                    ),
                    "output_tokens": result.get(
                        "output_tokens",
                        0,
                    ),
                    "cost": result.get(
                        "cost",
                        0.0,
                    ),
                    "error": result.get(
                        "error"
                    ),
                    "escalated": result.get(
                        "escalated",
                        False,
                    ),
                }
            )

        print(
            "    "
            f"Fast={fast_result['score']:.3f}, "
            f"Strong={strong_result['score']:.3f}, "
            f"Router={router_result['score']:.3f}"
        )

    # =====================================================
    # Overall Summaries
    # =====================================================

    summaries = [
        summarize_strategy(
            strategy,
            strategy_results[
                strategy
            ],
            task_type="All",
        )
        for strategy in STRATEGIES
    ]

    # =====================================================
    # Per-Task Summaries
    # =====================================================

    task_summaries: list[
        dict[str, Any]
    ] = []

    for strategy in STRATEGIES:

        strategy_cases = (
            strategy_results[
                strategy
            ]
        )

        for task_type in TASK_TYPES:

            task_cases = [
                result
                for result, case
                in zip(
                    strategy_cases,
                    dataset,
                )
                if (
                    case["task_type"]
                    .lower()
                    .strip()
                    == task_type
                )
            ]

            task_summary = (
                summarize_strategy(
                    strategy,
                    task_cases,
                    task_type=task_type,
                )
            )

            task_summaries.append(
                task_summary
            )

    # =====================================================
    # Apply Savings to Overall Results
    # =====================================================

    apply_savings(
        summaries
    )

    # =====================================================
    # Combine Results
    # =====================================================

    all_summaries = (
        summaries
        + task_summaries
    )

    # =====================================================
    # Save Results
    # =====================================================

    if save_results:

        save_evaluation_results(
            all_summaries
        )

    return (
        summaries,
        all_case_results,
    )


# =========================================================
# Print Results Table
# =========================================================

def print_results_table(
    summaries: list[dict[str, Any]],
) -> None:
    """
    Print overall strategy comparison table.
    """

    headers = [
        "Strategy",
        "Accuracy",
        "Requests",
        "Total Cost",
        "Avg Cost",
        "Fast Calls",
        "Strong Calls",
        "Escalations",
        "Savings vs Strong",
        "Savings %",
    ]

    rows = []

    for item in summaries:

        rows.append(
            [
                item["strategy"],
                (
                    f"{item['accuracy'] * 100:.2f}%"
                ),
                str(
                    item[
                        "total_requests"
                    ]
                ),
                (
                    f"${item['total_cost']:.8f}"
                ),
                (
                    f"$"
                    f"{item['average_cost_per_request']:.8f}"
                ),
                str(
                    item[
                        "fast_model_calls"
                    ]
                ),
                str(
                    item[
                        "strong_model_calls"
                    ]
                ),
                str(
                    item[
                        "escalations"
                    ]
                ),
                (
                    f"$"
                    f"{item['savings_vs_always_strong']:.8f}"
                ),
                (
                    f"{item['savings_percentage_vs_always_strong']:.2f}%"
                ),
            ]
        )

    widths = [
        max(
            len(headers[i]),
            *(
                len(row[i])
                for row in rows
            ),
        )
        for i in range(
            len(headers)
        )
    ]

    separator = (
        "-+-".join(
            "-" * width
            for width in widths
        )
    )

    print()
    print(
        "EVALUATION RESULTS"
    )
    print()

    print(
        " | ".join(
            header.ljust(
                widths[i]
            )
            for i, header
            in enumerate(headers)
        )
    )

    print(
        separator
    )

    for row in rows:

        print(
            " | ".join(
                value.ljust(
                    widths[i]
                )
                for i, value
                in enumerate(row)
            )
        )

    print()

    print(
        f"Saved results to: "
        f"{RESULTS_PATH}"
    )


# =========================================================
# Main
# =========================================================

def main() -> int:
    """
    Main evaluation entry point.
    """

    try:

        summaries, _ = (
            run_evaluation()
        )

        print_results_table(
            summaries
        )

        return 0

    except KeyboardInterrupt:

        print(
            "\nEvaluation cancelled "
            "by user."
        )

        return 130

    except Exception as error:

        print(
            f"Evaluation failed: "
            f"{error}"
        )

        return 1


# =========================================================
# Script Entry Point
# =========================================================

if __name__ == "__main__":

    sys.exit(
        main()
    )