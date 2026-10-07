# =========================================================
# router.py
# Stage 6 + Cost Tracking: Cost-aware routing engine
# =========================================================

from config import (
    COMPLEXITY_THRESHOLD,
    CONFIDENCE_THRESHOLD,
    FAST_MODEL_ID,
    STRONG_MODEL_ID,
)

from claude_client import call_model

from complexity_detector import calculate_complexity

from confidence_evaluator import (
    evaluate_with_fast_model,
)

from cost_tracker import (
    calculate_cost,
)


# =========================================================
# Cost Helper
# =========================================================

def _calculate_model_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate the cost of a single model call.

    cost_tracker expects:
        fast
        strong

    while the router works with actual model IDs.
    """

    if model == FAST_MODEL_ID:

        model_key = "fast"

    elif model == STRONG_MODEL_ID:

        model_key = "strong"

    else:

        raise ValueError(
            f"Unknown model for cost calculation: "
            f"{model}"
        )

    return float(
        calculate_cost(
            model=model_key,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    )


# =========================================================
# Cost Aggregation Helper
# =========================================================

def _calculate_total_cost(
    *,
    fast_input_tokens: int = 0,
    fast_output_tokens: int = 0,
    strong_input_tokens: int = 0,
    strong_output_tokens: int = 0,
) -> float:
    """
    Calculate total cost across all model calls.

    This is especially important for escalation:

        Fast call
             +
        Strong call
             =
        Total router cost
    """

    fast_cost = _calculate_model_cost(
        model=FAST_MODEL_ID,
        input_tokens=fast_input_tokens,
        output_tokens=fast_output_tokens,
    )

    strong_cost = _calculate_model_cost(
        model=STRONG_MODEL_ID,
        input_tokens=strong_input_tokens,
        output_tokens=strong_output_tokens,
    )

    return round(
        fast_cost + strong_cost,
        8,
    )


# =========================================================
# Standard Error Result
# =========================================================

def _build_error_result(
    *,
    error: str,
    initial_model: str,
    complexity_score: float,
    complexity_reasons: list[str],
    fast_answer: str = "",
    fast_confidence: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    actual_cost: float = 0.0,
    escalated: bool = False,
    final_model: str | None = None,
) -> dict:
    """
    Create a standardized routing result when
    an API operation fails.
    """

    if final_model is None:

        final_model = initial_model

    return {
        "answer": "",
        "initial_model": initial_model,
        "final_model": final_model,
        "confidence": fast_confidence,
        "complexity_score": complexity_score,
        "escalated": escalated,
        "escalation_reason": error,
        "complexity_reasons": complexity_reasons,

        # Combined token usage across all calls.
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,

        # Actual total cost across all calls.
        "actual_cost": actual_cost,

        # Debugging information.
        "fast_answer": fast_answer,
        "fast_confidence": fast_confidence,
        "error": error,
    }


# =========================================================
# Main Router
# =========================================================

def route_request(
    text: str,
    task_type: str,
) -> dict:
    """
    Route a request using complexity and fast-model confidence.

    Routing rules:

    1. Calculate complexity before calling any model.

    2. If complexity >= COMPLEXITY_THRESHOLD:
       call the strong model directly.

    3. Otherwise call the fast model.

    4. If fast confidence < CONFIDENCE_THRESHOLD OR
       needs_escalation == True:
       call the strong model.

    5. Otherwise accept the fast-model answer.

    Cost tracking:

    - Fast-only request:
          Fast cost

    - Strong-only request:
          Strong cost

    - Fast -> Strong escalation:
          Fast cost + Strong cost

    Returns a standardized routing result.
    """

    # =====================================================
    # STEP 1: Complexity Detection
    # =====================================================

    complexity_result = calculate_complexity(
        text=text,
        task_type=task_type,
    )

    complexity_score = (
        complexity_result["score"]
    )

    complexity_reasons = (
        complexity_result["reasons"]
    )

    # =====================================================
    # STEP 2: Direct Strong-Model Routing
    # =====================================================

    if (
        complexity_score
        >= COMPLEXITY_THRESHOLD
    ):

        strong_result = call_model(
            model=STRONG_MODEL_ID,
            prompt=text,
        )

        strong_input_tokens = (
            strong_result["input_tokens"]
        )

        strong_output_tokens = (
            strong_result["output_tokens"]
        )

        strong_cost = (
            _calculate_total_cost(
                strong_input_tokens=(
                    strong_input_tokens
                ),
                strong_output_tokens=(
                    strong_output_tokens
                ),
            )
        )

        if strong_result["error"]:

            return _build_error_result(
                error=(
                    "Strong model failed after direct "
                    "complexity routing: "
                    f"{strong_result['error']}"
                ),
                initial_model=STRONG_MODEL_ID,
                final_model=STRONG_MODEL_ID,
                complexity_score=complexity_score,
                complexity_reasons=complexity_reasons,
                input_tokens=strong_input_tokens,
                output_tokens=strong_output_tokens,
                actual_cost=strong_cost,
                escalated=False,
            )

        return {
            "answer": strong_result["text"],
            "initial_model": STRONG_MODEL_ID,
            "final_model": STRONG_MODEL_ID,
            "confidence": 1.0,
            "complexity_score": complexity_score,
            "escalated": False,
            "escalation_reason": (
                "Direct strong-model routing because "
                f"complexity score "
                f"{complexity_score:.2f} "
                f">= threshold "
                f"{COMPLEXITY_THRESHOLD:.2f}."
            ),
            "complexity_reasons": complexity_reasons,

            "input_tokens": strong_input_tokens,
            "output_tokens": strong_output_tokens,

            "actual_cost": strong_cost,

            "fast_answer": "",
            "fast_confidence": None,
            "error": None,
        }

    # =====================================================
    # STEP 3: Fast Model
    # =====================================================

    fast_result = evaluate_with_fast_model(
        task_prompt=text,
    )

    fast_answer = fast_result["answer"]

    fast_confidence = (
        fast_result["confidence"]
    )

    fast_input_tokens = (
        fast_result["input_tokens"]
    )

    fast_output_tokens = (
        fast_result["output_tokens"]
    )

    # Cost of first Fast call.
    fast_cost = _calculate_total_cost(
        fast_input_tokens=fast_input_tokens,
        fast_output_tokens=fast_output_tokens,
    )

    # =====================================================
    # STEP 4: Fast-Model API / Validation Error
    # =====================================================

    if not fast_result["valid"]:

        escalation_reason = (
            "Fast model result was invalid or unavailable: "
            + fast_result["reason"]
        )

        # -----------------------------------------------
        # Call Strong Model
        # -----------------------------------------------

        strong_result = call_model(
            model=STRONG_MODEL_ID,
            prompt=text,
        )

        strong_input_tokens = (
            strong_result["input_tokens"]
        )

        strong_output_tokens = (
            strong_result["output_tokens"]
        )

        # -----------------------------------------------
        # Total cost = Fast + Strong
        # -----------------------------------------------

        total_cost = _calculate_total_cost(
            fast_input_tokens=fast_input_tokens,
            fast_output_tokens=fast_output_tokens,
            strong_input_tokens=strong_input_tokens,
            strong_output_tokens=strong_output_tokens,
        )

        total_input_tokens = (
            fast_input_tokens
            + strong_input_tokens
        )

        total_output_tokens = (
            fast_output_tokens
            + strong_output_tokens
        )

        # -----------------------------------------------
        # Strong Model Also Failed
        # -----------------------------------------------

        if strong_result["error"]:

            return _build_error_result(
                error=(
                    "Fast model failed and strong model "
                    "also failed: "
                    f"{strong_result['error']}"
                ),
                initial_model=FAST_MODEL_ID,
                final_model=STRONG_MODEL_ID,
                complexity_score=complexity_score,
                complexity_reasons=complexity_reasons,
                fast_answer=fast_answer,
                fast_confidence=fast_confidence,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                actual_cost=total_cost,
                escalated=True,
            )

        # -----------------------------------------------
        # Strong Model Successful
        # -----------------------------------------------

        return {
            "answer": strong_result["text"],
            "initial_model": FAST_MODEL_ID,
            "final_model": STRONG_MODEL_ID,
            "confidence": fast_confidence,
            "complexity_score": complexity_score,
            "escalated": True,
            "escalation_reason": escalation_reason,
            "complexity_reasons": complexity_reasons,

            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,

            "actual_cost": total_cost,

            "fast_answer": fast_answer,
            "fast_confidence": fast_confidence,
            "error": None,
        }

    # =====================================================
    # STEP 5: Confidence-Based Escalation
    # =====================================================

    if (
        fast_confidence
        < CONFIDENCE_THRESHOLD
        or fast_result["needs_escalation"]
    ):

        if (
            fast_confidence
            < CONFIDENCE_THRESHOLD
        ):

            escalation_reason = (
                f"Fast-model confidence "
                f"{fast_confidence:.2f} is below "
                f"threshold "
                f"{CONFIDENCE_THRESHOLD:.2f}."
            )

        else:

            escalation_reason = (
                "Fast model explicitly requested "
                "escalation: "
                + fast_result["reason"]
            )

        # -----------------------------------------------
        # Call Strong Model
        # -----------------------------------------------

        strong_result = call_model(
            model=STRONG_MODEL_ID,
            prompt=text,
        )

        strong_input_tokens = (
            strong_result["input_tokens"]
        )

        strong_output_tokens = (
            strong_result["output_tokens"]
        )

        # -----------------------------------------------
        # Total cost = Fast + Strong
        # -----------------------------------------------

        total_cost = _calculate_total_cost(
            fast_input_tokens=fast_input_tokens,
            fast_output_tokens=fast_output_tokens,
            strong_input_tokens=strong_input_tokens,
            strong_output_tokens=strong_output_tokens,
        )

        total_input_tokens = (
            fast_input_tokens
            + strong_input_tokens
        )

        total_output_tokens = (
            fast_output_tokens
            + strong_output_tokens
        )

        # -----------------------------------------------
        # Strong Model Failed
        # -----------------------------------------------

        if strong_result["error"]:

            return {
                "answer": fast_answer,
                "initial_model": FAST_MODEL_ID,
                "final_model": FAST_MODEL_ID,
                "confidence": fast_confidence,
                "complexity_score": complexity_score,
                "escalated": True,
                "escalation_reason": (
                    escalation_reason
                    + " Strong model failed: "
                    + strong_result["error"]
                ),
                "complexity_reasons": complexity_reasons,

                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,

                "actual_cost": total_cost,

                "fast_answer": fast_answer,
                "fast_confidence": fast_confidence,
                "error": strong_result["error"],
            }

        # -----------------------------------------------
        # Strong Model Successful
        # -----------------------------------------------

        return {
            "answer": strong_result["text"],
            "initial_model": FAST_MODEL_ID,
            "final_model": STRONG_MODEL_ID,
            "confidence": fast_confidence,
            "complexity_score": complexity_score,
            "escalated": True,
            "escalation_reason": escalation_reason,
            "complexity_reasons": complexity_reasons,

            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,

            "actual_cost": total_cost,

            "fast_answer": fast_answer,
            "fast_confidence": fast_confidence,
            "error": None,
        }

    # =====================================================
    # STEP 6: Accept Fast-Model Answer
    # =====================================================

    return {
        "answer": fast_answer,
        "initial_model": FAST_MODEL_ID,
        "final_model": FAST_MODEL_ID,
        "confidence": fast_confidence,
        "complexity_score": complexity_score,
        "escalated": False,
        "escalation_reason": "",
        "complexity_reasons": complexity_reasons,

        "input_tokens": fast_input_tokens,
        "output_tokens": fast_output_tokens,

        "actual_cost": fast_cost,

        "fast_answer": fast_answer,
        "fast_confidence": fast_confidence,
        "error": None,
    }