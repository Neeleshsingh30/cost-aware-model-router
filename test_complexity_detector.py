# =========================================================
# test_complexity_detector.py
# Stage 5 unit-test-like examples
# =========================================================

from complexity_detector import calculate_complexity


def test_simple_classification():
    print("=" * 60)
    print("TEST 1: SIMPLE CLASSIFICATION")
    print("=" * 60)

    text = "I was charged twice for my order."

    result = calculate_complexity(
        text=text,
        task_type="classification",
    )

    print("Input:", text)
    print("Result:", result)

    assert 0 <= result["score"] <= 1
    assert result["score"] < 0.60

    print("PASS")


def test_simple_extraction():
    print("=" * 60)
    print("TEST 2: SIMPLE EXTRACTION")
    print("=" * 60)

    text = (
        "Rahul Sharma purchased a Dell laptop "
        "for Rs. 75000."
    )

    result = calculate_complexity(
        text=text,
        task_type="extraction",
    )

    print("Input:", text)
    print("Result:", result)

    assert 0 <= result["score"] <= 1
    assert result["score"] < 0.60

    print("PASS")


def test_long_summarisation():
    print("=" * 60)
    print("TEST 3: LONG SUMMARISATION")
    print("=" * 60)

    text = " ".join(
        [
            "Machine learning is a branch of artificial intelligence."
        ]
        * 500
    )

    result = calculate_complexity(
        text=text,
        task_type="summarisation",
    )

    print("Input length:", len(text))
    print("Result:", result)

    assert 0 <= result["score"] <= 1
    assert "Very long input" in result["reasons"]
    assert "Long summarisation input" in result["reasons"]

    print("PASS")


def test_complex_qa():
    print("=" * 60)
    print("TEST 4: COMPLEX Q&A")
    print("=" * 60)

    text = """
    Analyze the following business situation and explain why
    revenue decreased despite increasing customer acquisition.

    Compare the performance of the two regions, evaluate the
    possible causes, determine which explanation is most likely,
    and justify your conclusion.

    The company operates across multiple markets and has several
    product categories. Customer acquisition increased by 25 percent,
    but conversion decreased by 12 percent. Customer retention also
    declined during the same period.

    First, analyze the acquisition data.
    Second, compare conversion rates.
    Third, evaluate customer retention.
    Finally, determine the most likely reason for the revenue decline.
    """

    result = calculate_complexity(
        text=text,
        task_type="qa",
    )

    print("Input length:", len(text))
    print("Result:", result)

    assert 0 <= result["score"] <= 1

    assert (
        "Requires reasoning or analysis"
        in result["reasons"]
    )

    assert (
        "Multiple instructions"
        in result["reasons"]
    )

    assert (
        "Requires comparison or evaluation"
        in result["reasons"]
    )

    assert result["score"] >= 0.60

    print("PASS")


def main():
    test_simple_classification()
    test_simple_extraction()
    test_long_summarisation()
    test_complex_qa()

    print()
    print("=" * 60)
    print("ALL STAGE 5 COMPLEXITY TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()