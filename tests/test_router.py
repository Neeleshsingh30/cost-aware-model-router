# =========================================================
# test_router.py
# Stage 6: Routing engine tests
# =========================================================

from unittest.mock import patch

import router


def test_simple_request_fast_model():
    """
    Simple request:
    complexity < 0.70
    fast confidence >= 0.75
    expected -> FAST
    """

    fake_complexity = {
        "score": 0.10,
        "reasons": [],
    }

    fake_fast_result = {
        "answer": "billing",
        "confidence": 0.95,
        "needs_escalation": False,
        "reason": "Clear request.",
        "valid": True,
        "model": "deepseek-v4-flash",
        "input_tokens": 100,
        "output_tokens": 20,
        "latency_ms": 500,
    }

    with patch(
        "router.calculate_complexity",
        return_value=fake_complexity,
    ), patch(
        "router.evaluate_with_fast_model",
        return_value=fake_fast_result,
    ), patch(
        "router.call_model",
    ) as mock_call_model:

        result = router.route_request(
            text="Classify this request.",
            task_type="classification",
        )

    assert result["final_model"] == router.FAST_MODEL_ID
    assert result["escalated"] is False
    assert result["confidence"] == 0.95

    # Strong model must not be called.
    mock_call_model.assert_not_called()

    print("PASS: Simple request -> Fast model")


def test_complex_request_direct_strong():
    """
    Complex request:
    complexity >= 0.70
    expected -> STRONG directly
    """

    fake_complexity = {
        "score": 0.85,
        "reasons": [
            "Requires reasoning or analysis",
            "Requires comparison or evaluation",
        ],
    }

    fake_strong_result = {
        "text": "Strong model answer.",
        "input_tokens": 300,
        "output_tokens": 100,
        "model": router.STRONG_MODEL_ID,
        "latency_ms": 1000,
        "error": None,
    }

    with patch(
        "router.calculate_complexity",
        return_value=fake_complexity,
    ), patch(
        "router.call_model",
        return_value=fake_strong_result,
    ) as mock_call_model, patch(
        "router.evaluate_with_fast_model",
    ) as mock_fast:

        result = router.route_request(
            text="Compare and evaluate these two systems.",
            task_type="qa",
        )

    assert result["final_model"] == router.STRONG_MODEL_ID
    assert result["escalated"] is False
    assert result["answer"] == "Strong model answer."

    # Fast model must NOT be called.
    mock_fast.assert_not_called()

    # Strong model called exactly once.
    mock_call_model.assert_called_once()

    print("PASS: Complex request -> Strong model directly")


def test_low_confidence_escalation():
    """
    Complexity is low, so fast model is attempted.
    Fast confidence < 0.75.
    Expected -> Strong model.
    """

    fake_complexity = {
        "score": 0.20,
        "reasons": [],
    }

    fake_fast_result = {
        "answer": "Possibly billing.",
        "confidence": 0.40,
        "needs_escalation": False,
        "reason": "Uncertain answer.",
        "valid": True,
        "model": router.FAST_MODEL_ID,
        "input_tokens": 100,
        "output_tokens": 30,
        "latency_ms": 500,
    }

    fake_strong_result = {
        "text": "Confirmed billing issue.",
        "input_tokens": 120,
        "output_tokens": 40,
        "model": router.STRONG_MODEL_ID,
        "latency_ms": 1000,
        "error": None,
    }

    with patch(
        "router.calculate_complexity",
        return_value=fake_complexity,
    ), patch(
        "router.evaluate_with_fast_model",
        return_value=fake_fast_result,
    ), patch(
        "router.call_model",
        return_value=fake_strong_result,
    ):

        result = router.route_request(
            text="Classify this ambiguous request.",
            task_type="classification",
        )

    assert result["initial_model"] == router.FAST_MODEL_ID
    assert result["final_model"] == router.STRONG_MODEL_ID
    assert result["escalated"] is True

    # Strong answer must replace fast answer.
    assert result["answer"] == "Confirmed billing issue."

    # Original fast answer preserved.
    assert result["fast_answer"] == "Possibly billing."

    print("PASS: Low confidence -> Strong model")


def test_explicit_escalation():
    """
    Complexity is low.
    Fast model has sufficient confidence but explicitly
    requests escalation.
    Expected -> Strong model.
    """

    fake_complexity = {
        "score": 0.20,
        "reasons": [],
    }

    fake_fast_result = {
        "answer": "Potential answer.",
        "confidence": 0.90,
        "needs_escalation": True,
        "reason": "Requires stronger reasoning.",
        "valid": True,
        "model": router.FAST_MODEL_ID,
        "input_tokens": 100,
        "output_tokens": 30,
        "latency_ms": 500,
    }

    fake_strong_result = {
        "text": "Strong final answer.",
        "input_tokens": 120,
        "output_tokens": 40,
        "model": router.STRONG_MODEL_ID,
        "latency_ms": 1000,
        "error": None,
    }

    with patch(
        "router.calculate_complexity",
        return_value=fake_complexity,
    ), patch(
        "router.evaluate_with_fast_model",
        return_value=fake_fast_result,
    ), patch(
        "router.call_model",
        return_value=fake_strong_result,
    ):

        result = router.route_request(
            text="Analyze this difficult case.",
            task_type="qa",
        )

    assert result["final_model"] == router.STRONG_MODEL_ID
    assert result["escalated"] is True
    assert result["answer"] == "Strong final answer."
    assert result["fast_answer"] == "Potential answer."

    print("PASS: Explicit escalation -> Strong model")


def test_fast_model_accepted():
    """
    Complexity below threshold.
    Confidence above threshold.
    No explicit escalation.
    Expected -> Fast.
    """

    fake_complexity = {
        "score": 0.30,
        "reasons": [
            "Short input",
        ],
    }

    fake_fast_result = {
        "answer": "Customer is asking about billing.",
        "confidence": 0.88,
        "needs_escalation": False,
        "reason": "Straightforward classification.",
        "valid": True,
        "model": router.FAST_MODEL_ID,
        "input_tokens": 100,
        "output_tokens": 20,
        "latency_ms": 500,
    }

    with patch(
        "router.calculate_complexity",
        return_value=fake_complexity,
    ), patch(
        "router.evaluate_with_fast_model",
        return_value=fake_fast_result,
    ), patch(
        "router.call_model",
    ) as mock_call_model:

        result = router.route_request(
            text="What category is this?",
            task_type="classification",
        )

    assert result["answer"] == (
        "Customer is asking about billing."
    )

    assert result["final_model"] == router.FAST_MODEL_ID
    assert result["escalated"] is False

    mock_call_model.assert_not_called()

    print("PASS: High confidence -> Fast accepted")


def main():
    print("=" * 60)
    print("STAGE 6 ROUTER TESTS")
    print("=" * 60)

    test_simple_request_fast_model()
    test_complex_request_direct_strong()
    test_low_confidence_escalation()
    test_explicit_escalation()
    test_fast_model_accepted()

    print()
    print("=" * 60)
    print("ALL STAGE 6 ROUTER TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()