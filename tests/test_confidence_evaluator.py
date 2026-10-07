# =========================================================
# test_confidence_evaluator.py
# Stage 4 tests
# =========================================================

from confidence_evaluator import (
    parse_confidence_response,
)


def test_high_confidence():
    print("=" * 60)
    print("TEST 1: HIGH CONFIDENCE")
    print("=" * 60)

    response = """
    {
        "answer": "Billing",
        "confidence": 0.95,
        "needs_escalation": false,
        "reason": "The request clearly describes a duplicate charge."
    }
    """

    result = parse_confidence_response(response)

    print(result)

    assert result["valid"] is True
    assert result["confidence"] == 0.95
    assert result["needs_escalation"] is False

    print("PASS")


def test_low_confidence():
    print("=" * 60)
    print("TEST 2: LOW CONFIDENCE")
    print("=" * 60)

    response = """
    {
        "answer": "Technical",
        "confidence": 0.42,
        "needs_escalation": false,
        "reason": "The request is ambiguous and could belong to multiple categories."
    }
    """

    result = parse_confidence_response(response)

    print(result)

    assert result["valid"] is True
    assert result["confidence"] == 0.42

    # Confidence below 0.75 must trigger escalation.
    assert result["needs_escalation"] is True

    print("PASS")


def test_explicit_escalation():
    print("=" * 60)
    print("TEST 3: EXPLICIT ESCALATION")
    print("=" * 60)

    response = """
    {
        "answer": "The answer may be related to multiple causes.",
        "confidence": 0.90,
        "needs_escalation": true,
        "reason": "The task requires deeper reasoning."
    }
    """

    result = parse_confidence_response(response)

    print(result)

    assert result["valid"] is True
    assert result["confidence"] == 0.90

    # Explicit escalation must be respected.
    assert result["needs_escalation"] is True

    print("PASS")


def test_invalid_json():
    print("=" * 60)
    print("TEST 4: INVALID JSON")
    print("=" * 60)

    response = """
    {
        "answer": "Billing",
        "confidence": 0.95,
        "needs_escalation": false,
        "reason": "Clear billing issue."
    """

    result = parse_confidence_response(response)

    print(result)

    # Invalid JSON must safely trigger escalation.
    assert result["valid"] is False
    assert result["needs_escalation"] is True
    assert result["confidence"] == 0.0

    print("PASS")


def test_confidence_out_of_range():
    print("=" * 60)
    print("TEST 5: CONFIDENCE OUT OF RANGE")
    print("=" * 60)

    response = """
    {
        "answer": "Billing",
        "confidence": 1.5,
        "needs_escalation": false,
        "reason": "Very clear request."
    }
    """

    result = parse_confidence_response(response)

    print(result)

    assert result["valid"] is False
    assert result["needs_escalation"] is True
    assert result["confidence"] == 0.0

    print("PASS")


def main():
    test_high_confidence()
    test_low_confidence()
    test_explicit_escalation()
    test_invalid_json()
    test_confidence_out_of_range()

    print()
    print("=" * 60)
    print("ALL STAGE 4 TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()