# =========================================================
# router.py
# Stage 6 + Cost Tracking: Cost-aware routing engine
# =========================================================

from .config import (
    COMPLEXITY_THRESHOLD,
    CONFIDENCE_THRESHOLD,
    FAST_MODEL_ID,
    STRONG_MODEL_ID,
)

from .claude_client import call_model

from .complexity_detector import calculate_complexity

from .confidence_evaluator import (
    evaluate_with_fast_model,
)
from .answer_verifier import (
    build_answer_review_prompt,
    requires_independent_review,
)

from .cost_tracker import (
    calculate_cost,
)


# =========================================================
# Cost Helper
# =========================================================

def _calculate_model_cost(
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
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

    if input_tokens is None or output_tokens is None:
        return None
    cost = calculate_cost(model=model_key, input_tokens=input_tokens, output_tokens=output_tokens)
    return float(cost) if cost is not None else None


# =========================================================
# Cost Aggregation Helper
# =========================================================

def _calculate_total_cost(
    *,
    fast_called: bool = False,
    fast_input_tokens: int | None = None,
    fast_output_tokens: int | None = None,
    strong_called: bool = False,
    strong_input_tokens: int | None = None,
    strong_output_tokens: int | None = None,
) -> float | None:
    """
    Calculate total cost across all model calls.

    This is especially important for escalation:

        Fast call
             +
        Strong call
             =
        Total router cost
    """

    costs = []
    for model, called, input_count, output_count in (
        (FAST_MODEL_ID, fast_called, fast_input_tokens, fast_output_tokens),
        (STRONG_MODEL_ID, strong_called, strong_input_tokens, strong_output_tokens),
    ):
        if not called:
            continue
        cost = _calculate_model_cost(model, input_count, output_count)
        if cost is None:
            return None
        costs.append(cost)
    return round(sum(costs), 8)


def _sum_token_counts(first: int | None, second: int | None) -> int | None:
    if first is None or second is None:
        return None
    return first + second


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
    fast_confidence: float | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    actual_cost: float = 0.0,
    latency_ms: float | None = None,
    escalated: bool = False,
    final_model: str | None = None,
    routing_decision: str = "failed",
    escalation_reason: str = "",
    routing_reason: str = "",
    confidence_source: str | None = None,
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
        "confidence_source": confidence_source,
        "complexity_score": complexity_score,
        "escalated": escalated,
        "routing_decision": routing_decision,
        "routing_reason": routing_reason,
        "escalation_reason": escalation_reason,
        "complexity_reasons": complexity_reasons,

        # Combined token usage across all calls.
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,

        # Actual total cost across all calls.
        "actual_cost": actual_cost,
        "latency_ms": latency_ms,

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

        strong_input_tokens = strong_result.get("input_tokens")
        strong_output_tokens = strong_result.get("output_tokens")

        strong_cost = (
            _calculate_total_cost(
                strong_called=True,
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
                latency_ms=strong_result.get("latency_ms"),
                escalated=False,
                routing_decision="direct_strong_failed",
                routing_reason="high_complexity",
            )

        return {
            "answer": strong_result["text"],
            "initial_model": STRONG_MODEL_ID,
            "final_model": STRONG_MODEL_ID,
            "confidence": None,
            "confidence_source": None,
            "complexity_score": complexity_score,
            "escalated": False,
            "routing_decision": "direct_strong",
            "routing_reason": "high_complexity",
            "escalation_reason": "",
            "complexity_reasons": complexity_reasons,

            "input_tokens": strong_input_tokens,
            "output_tokens": strong_output_tokens,

            "actual_cost": strong_cost,
            "latency_ms": strong_result.get("latency_ms"),

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

    fast_input_tokens = fast_result.get("input_tokens")
    fast_output_tokens = fast_result.get("output_tokens")

    # Cost of first Fast call.
    fast_cost = _calculate_total_cost(
        fast_called=True,
        fast_input_tokens=fast_input_tokens,
        fast_output_tokens=fast_output_tokens,
    )
    fast_latency_ms = fast_result.get("latency_ms")
    independent_review_required = requires_independent_review(text)

    # A provider call failure is terminal for this request. Retrying it
    # immediately with the strong model can incur another charge while
    # authentication, quota, or connectivity problems affect both models.
    if fast_result.get("provider_error", False):
        return _build_error_result(
            error=fast_result["reason"],
            initial_model=FAST_MODEL_ID,
            final_model=FAST_MODEL_ID,
            complexity_score=complexity_score,
            complexity_reasons=complexity_reasons,
            input_tokens=fast_input_tokens,
            output_tokens=fast_output_tokens,
            actual_cost=fast_cost,
            latency_ms=fast_latency_ms,
            escalated=False,
            routing_decision="fast_model_failed",
            routing_reason="fast_provider_error",
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

        strong_input_tokens = strong_result.get("input_tokens")
        strong_output_tokens = strong_result.get("output_tokens")

        # -----------------------------------------------
        # Total cost = Fast + Strong
        # -----------------------------------------------

        total_cost = _calculate_total_cost(
            fast_called=True,
            fast_input_tokens=fast_input_tokens,
            fast_output_tokens=fast_output_tokens,
            strong_called=True,
            strong_input_tokens=strong_input_tokens,
            strong_output_tokens=strong_output_tokens,
        )

        total_input_tokens = _sum_token_counts(fast_input_tokens, strong_input_tokens)
        total_output_tokens = _sum_token_counts(fast_output_tokens, strong_output_tokens)
        total_latency_ms = sum(
            value for value in (fast_latency_ms, strong_result.get("latency_ms"))
            if value is not None
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
                fast_confidence=None,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                actual_cost=total_cost,
                latency_ms=total_latency_ms,
                escalated=True,
                routing_decision="escalation_failed",
                escalation_reason="invalid_fast_response",
                routing_reason="invalid_fast_response",
            )

        # -----------------------------------------------
        # Strong Model Successful
        # -----------------------------------------------

        return {
            "answer": strong_result["text"],
            "initial_model": FAST_MODEL_ID,
            "final_model": STRONG_MODEL_ID,
            "confidence": fast_confidence if fast_result["valid"] else None,
            "confidence_source": "fast_model_self_reported" if fast_result["valid"] else None,
            "complexity_score": complexity_score,
            "escalated": True,
            "routing_decision": "escalated_to_strong",
            "routing_reason": "invalid_fast_response",
            "escalation_reason": "invalid_fast_response",
            "complexity_reasons": complexity_reasons,

            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,

            "actual_cost": total_cost,
            "latency_ms": total_latency_ms,

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
        or independent_review_required
    ):

        if (
            fast_confidence
            < CONFIDENCE_THRESHOLD
        ):

            escalation_reason = "low_confidence"

        else:

            escalation_reason = (
                "independent_answer_review"
                if independent_review_required
                else "fast_model_requested_escalation"
            )

        # -----------------------------------------------
        # Call Strong Model
        # -----------------------------------------------

        strong_result = call_model(
            model=STRONG_MODEL_ID,
            prompt=(
                build_answer_review_prompt(text, fast_answer)
                if independent_review_required
                else text
            ),
        )

        strong_input_tokens = strong_result.get("input_tokens")
        strong_output_tokens = strong_result.get("output_tokens")

        # -----------------------------------------------
        # Total cost = Fast + Strong
        # -----------------------------------------------

        total_cost = _calculate_total_cost(
            fast_called=True,
            fast_input_tokens=fast_input_tokens,
            fast_output_tokens=fast_output_tokens,
            strong_called=True,
            strong_input_tokens=strong_input_tokens,
            strong_output_tokens=strong_output_tokens,
        )

        total_input_tokens = _sum_token_counts(fast_input_tokens, strong_input_tokens)
        total_output_tokens = _sum_token_counts(fast_output_tokens, strong_output_tokens)
        total_latency_ms = sum(
            value for value in (fast_latency_ms, strong_result.get("latency_ms"))
            if value is not None
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
                "latency_ms": total_latency_ms,
                "confidence_source": "fast_model_self_reported",
                "routing_decision": "escalation_failed",
                "routing_reason": escalation_reason,
                "escalation_reason": escalation_reason,

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
            "confidence_source": "fast_model_self_reported",
            "complexity_score": complexity_score,
            "escalated": True,
            "routing_decision": "escalated_to_strong",
            "routing_reason": escalation_reason,
            "escalation_reason": escalation_reason,
            "complexity_reasons": complexity_reasons,

            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,

            "actual_cost": total_cost,
            "latency_ms": total_latency_ms,

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
        "confidence_source": "fast_model_self_reported",
        "complexity_score": complexity_score,
        "escalated": False,
        "routing_decision": "fast_model",
        "routing_reason": "confidence_above_threshold",
        "escalation_reason": "",
        "complexity_reasons": complexity_reasons,

        "input_tokens": fast_input_tokens,
        "output_tokens": fast_output_tokens,

        "actual_cost": fast_cost,
        "latency_ms": fast_latency_ms,

        "fast_answer": fast_answer,
        "fast_confidence": fast_confidence,
        "error": None,
    }
