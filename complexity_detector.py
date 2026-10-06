# =========================================================
# complexity_detector.py
# Stage 5: Request complexity detection
# =========================================================

import os

from dotenv import load_dotenv


load_dotenv()


# ---------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------

LONG_INPUT_THRESHOLD = int(
    os.getenv("LONG_INPUT_THRESHOLD", "2000")
)

VERY_LONG_INPUT_THRESHOLD = int(
    os.getenv("VERY_LONG_INPUT_THRESHOLD", "5000")
)

LONG_QA_CONTEXT_THRESHOLD = int(
    os.getenv("LONG_QA_CONTEXT_THRESHOLD", "3000")
)

LONG_SUMMARISATION_THRESHOLD = int(
    os.getenv("LONG_SUMMARISATION_THRESHOLD", "3000")
)

COMPLEXITY_THRESHOLD = float(
    os.getenv("COMPLEXITY_THRESHOLD", "0.60")
)


# ---------------------------------------------------------
# Explainable signal weights
# ---------------------------------------------------------

INPUT_LENGTH_WEIGHT = 0.25
REASONING_WEIGHT = 0.20
MULTI_INSTRUCTION_WEIGHT = 0.15
TASK_COMPLEXITY_WEIGHT = 0.15
COMPARISON_WEIGHT = 0.15
LONG_CONTEXT_WEIGHT = 0.10


# ---------------------------------------------------------
# Explainable keyword groups
# ---------------------------------------------------------

REASONING_KEYWORDS = {
    "explain why",
    "why",
    "analyze",
    "analyse",
    "reason",
    "reasoning",
    "derive",
    "justify",
    "evaluate",
    "investigate",
    "determine",
}

COMPARISON_KEYWORDS = {
    "compare",
    "comparison",
    "versus",
    "vs",
    "difference",
    "differences",
    "better",
    "pros and cons",
    "trade-off",
    "tradeoff",
}

MULTI_INSTRUCTION_MARKERS = {
    "step 1",
    "step 2",
    "step 3",
    "first",
    "second",
    "third",
    "then",
    "also",
    "additionally",
    "finally",
}


def _contains_any(text: str, keywords: set[str]) -> bool:
    """
    Return True if any keyword or phrase exists in the text.
    """

    text_lower = text.lower()

    return any(
        keyword in text_lower
        for keyword in keywords
    )


def _calculate_length_score(text_length: int) -> float:
    """
    Convert input length into a 0-1 score.
    """

    if text_length < LONG_INPUT_THRESHOLD:
        return 0.0

    if text_length >= VERY_LONG_INPUT_THRESHOLD:
        return 1.0

    range_size = (
        VERY_LONG_INPUT_THRESHOLD
        - LONG_INPUT_THRESHOLD
    )

    return (
        text_length - LONG_INPUT_THRESHOLD
    ) / range_size


def calculate_complexity(
    text: str,
    task_type: str,
) -> dict:
    """
    Calculate a lightweight, explainable complexity score.

    Parameters
    ----------
    text:
        User input or task context.

    task_type:
        classification, extraction, summarisation, or qa.

    Returns
    -------
    dict
        {
            "score": float,
            "reasons": list[str]
        }

    This function does NOT call an LLM.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    if not text.strip():
        return {
            "score": 0.0,
            "reasons": [],
        }

    task_type = task_type.lower().strip()

    if task_type not in {
        "classification",
        "extraction",
        "summarisation",
        "qa",
    }:
        raise ValueError(
            "Unsupported task_type. Expected "
            "classification, extraction, summarisation, or qa."
        )

    text_length = len(text)

    score = 0.0
    reasons = []

    # -----------------------------------------------------
    # 1. Input length
    # -----------------------------------------------------

    length_score = _calculate_length_score(text_length)

    if length_score > 0:
        score += (
            length_score
            * INPUT_LENGTH_WEIGHT
        )

        if text_length >= VERY_LONG_INPUT_THRESHOLD:
            reasons.append("Very long input")
        else:
            reasons.append("Long input")

    # -----------------------------------------------------
    # 2. Reasoning / analysis language
    # -----------------------------------------------------

    requires_reasoning = _contains_any(
        text,
        REASONING_KEYWORDS,
    )

    if requires_reasoning:
        score += REASONING_WEIGHT

        reasons.append(
            "Requires reasoning or analysis"
        )

    # -----------------------------------------------------
    # 3. Multiple instructions
    # -----------------------------------------------------

    instruction_count = sum(
        1
        for marker in MULTI_INSTRUCTION_MARKERS
        if marker in text.lower()
    )

    if instruction_count >= 2:
        score += MULTI_INSTRUCTION_WEIGHT

        reasons.append(
            "Multiple instructions"
        )

    # -----------------------------------------------------
    # 4. Task-specific complexity
    # -----------------------------------------------------

    if task_type == "qa":

        # Long context
        if text_length >= LONG_QA_CONTEXT_THRESHOLD:
            score += LONG_CONTEXT_WEIGHT

            reasons.append(
                "Long Q&A context"
            )

        # Complex Q&A reasoning
        #
        # A Q&A request can be complex even when the
        # context is relatively short. If it requires
        # both reasoning and comparison, add a
        # task-specific complexity signal.
        requires_comparison = _contains_any(
            text,
            COMPARISON_KEYWORDS,
        )

        if (
            requires_reasoning
            and requires_comparison
        ):
            score += TASK_COMPLEXITY_WEIGHT

            reasons.append(
                "Complex Q&A reasoning"
            )

    elif task_type == "summarisation":

        if text_length >= LONG_SUMMARISATION_THRESHOLD:
            score += LONG_CONTEXT_WEIGHT

            reasons.append(
                "Long summarisation input"
            )

    elif task_type == "extraction":

        if text_length >= LONG_INPUT_THRESHOLD:
            score += TASK_COMPLEXITY_WEIGHT

            reasons.append(
                "Large extraction input"
            )

    elif task_type == "classification":

        # Classification receives no additional
        # task-specific complexity score.
        pass

    # -----------------------------------------------------
    # 5. Comparison / evaluation requirements
    # -----------------------------------------------------

    if _contains_any(
        text,
        COMPARISON_KEYWORDS,
    ):
        score += COMPARISON_WEIGHT

        reasons.append(
            "Requires comparison or evaluation"
        )

    # -----------------------------------------------------
    # Final score
    # -----------------------------------------------------

    score = min(score, 1.0)

    return {
        "score": round(score, 2),
        "reasons": reasons,
    }