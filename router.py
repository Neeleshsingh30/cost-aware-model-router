# =========================================================
# router.py
# Stage 6: Cost-aware routing engine
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
) -> dict:
    """
    Create a standardized routing result when an API
    operation fails.
    """

    return {
        "answer": "",
        "initial_model": initial_model,
        "final_model": initial_model,
        "confidence": fast_confidence,
        "complexity_score": complexity_score,
        "escalated": False,
        "escalation_reason": error,
        "complexity_reasons": complexity_reasons,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,

        # Debug/logging information.
        "fast_answer": fast_answer,
        "fast_confidence": fast_confidence,
        "error": error,
    }


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

    The strong model is not called unnecessarily.

    Returns a standardized routing result.
    """

    # -----------------------------------------------------
    # STEP 1: Complexity detection
    # -----------------------------------------------------

    complexity_result = calculate_complexity(
        text=text,
        task_type=task_type,
    )

    complexity_score = complexity_result["score"]
    complexity_reasons = complexity_result["reasons"]

    # -----------------------------------------------------
    # STEP 2: Direct strong-model routing
    # -----------------------------------------------------

    if complexity_score >= COMPLEXITY_THRESHOLD:

        strong_result = call_model(
            model=STRONG_MODEL_ID,
            prompt=text,
        )

        if strong_result["error"]:

            return _build_error_result(
                error=(
                    "Strong model failed after direct "
                    f"complexity routing: "
                    f"{strong_result['error']}"
                ),
                initial_model=STRONG_MODEL_ID,
                complexity_score=complexity_score,
                complexity_reasons=complexity_reasons,
                input_tokens=strong_result["input_tokens"],
                output_tokens=strong_result["output_tokens"],
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
                f"complexity score {complexity_score:.2f} "
                f">= threshold {COMPLEXITY_THRESHOLD:.2f}."
            ),
            "complexity_reasons": complexity_reasons,
            "input_tokens": strong_result["input_tokens"],
            "output_tokens": strong_result["output_tokens"],

            # Debug/logging.
            "fast_answer": "",
            "fast_confidence": None,
            "error": None,
        }

    # -----------------------------------------------------
    # STEP 3: Fast model
    # -----------------------------------------------------

    fast_result = evaluate_with_fast_model(
        task_prompt=text,
    )

    fast_answer = fast_result["answer"]
    fast_confidence = fast_result["confidence"]

    # -----------------------------------------------------
    # STEP 4: Fast-model API/validation error
    # -----------------------------------------------------

    if not fast_result["valid"]:

        # The confidence evaluator already converts malformed
        # JSON and API errors into needs_escalation=True.

        escalation_reason = (
            "Fast model result was invalid or unavailable: "
            + fast_result["reason"]
        )

        strong_result = call_model(
            model=STRONG_MODEL_ID,
            prompt=text,
        )

        if strong_result["error"]:

            return _build_error_result(
                error=(
                    "Fast model failed and strong model "
                    f"also failed: "
                    f"{strong_result['error']}"
                ),
                initial_model=FAST_MODEL_ID,
                complexity_score=complexity_score,
                complexity_reasons=complexity_reasons,
                fast_answer=fast_answer,
                fast_confidence=fast_confidence,
                input_tokens=(
                    fast_result["input_tokens"]
                    + strong_result["input_tokens"]
                ),
                output_tokens=(
                    fast_result["output_tokens"]
                    + strong_result["output_tokens"]
                ),
            )

        return {
            "answer": strong_result["text"],
            "initial_model": FAST_MODEL_ID,
            "final_model": STRONG_MODEL_ID,
            "confidence": fast_confidence,
            "complexity_score": complexity_score,
            "escalated": True,
            "escalation_reason": escalation_reason,
            "complexity_reasons": complexity_reasons,
            "input_tokens": (
                fast_result["input_tokens"]
                + strong_result["input_tokens"]
            ),
            "output_tokens": (
                fast_result["output_tokens"]
                + strong_result["output_tokens"]
            ),

            # Preserve original fast-model answer.
            "fast_answer": fast_answer,
            "fast_confidence": fast_confidence,
            "error": None,
        }

    # -----------------------------------------------------
    # STEP 5: Confidence-based escalation
    # -----------------------------------------------------

    if (
        fast_confidence < CONFIDENCE_THRESHOLD
        or fast_result["needs_escalation"]
    ):

        if fast_confidence < CONFIDENCE_THRESHOLD:
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

        strong_result = call_model(
            model=STRONG_MODEL_ID,
            prompt=text,
        )

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
                "input_tokens": (
                    fast_result["input_tokens"]
                    + strong_result["input_tokens"]
                ),
                "output_tokens": (
                    fast_result["output_tokens"]
                    + strong_result["output_tokens"]
                ),

                # Preserve fast answer.
                "fast_answer": fast_answer,
                "fast_confidence": fast_confidence,
                "error": strong_result["error"],
            }

        # Strong-model answer becomes final answer.
        return {
            "answer": strong_result["text"],
            "initial_model": FAST_MODEL_ID,
            "final_model": STRONG_MODEL_ID,
            "confidence": fast_confidence,
            "complexity_score": complexity_score,
            "escalated": True,
            "escalation_reason": escalation_reason,
            "complexity_reasons": complexity_reasons,
            "input_tokens": (
                fast_result["input_tokens"]
                + strong_result["input_tokens"]
            ),
            "output_tokens": (
                fast_result["output_tokens"]
                + strong_result["output_tokens"]
            ),

            # Preserve original fast-model answer.
            "fast_answer": fast_answer,
            "fast_confidence": fast_confidence,
            "error": None,
        }

    # -----------------------------------------------------
    # STEP 6: Accept fast-model answer
    # -----------------------------------------------------

    return {
        "answer": fast_answer,
        "initial_model": FAST_MODEL_ID,
        "final_model": FAST_MODEL_ID,
        "confidence": fast_confidence,
        "complexity_score": complexity_score,
        "escalated": False,
        "escalation_reason": "",
        "complexity_reasons": complexity_reasons,
        "input_tokens": fast_result["input_tokens"],
        "output_tokens": fast_result["output_tokens"],

        # Debug/logging.
        "fast_answer": fast_answer,
        "fast_confidence": fast_confidence,
        "error": None,
    }