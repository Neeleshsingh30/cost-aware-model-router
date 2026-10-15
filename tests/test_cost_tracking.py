from decimal import Decimal
from unittest.mock import patch

from backend.app.core import cost_tracker, router


def test_escalation_cost_and_strong_baseline_include_both_calls():
    prices = {
        "fast": {"input_per_mtok": 0.060, "output_per_mtok": 0.12},
        "strong": {"input_per_mtok": 2.0, "output_per_mtok": 10.0},
    }
    with patch.dict(cost_tracker.MODEL_PRICING, prices):
        with patch.object(router, "calculate_cost", side_effect=cost_tracker.calculate_cost):
            actual = router._calculate_total_cost(
                fast_called=True,
                fast_input_tokens=1_000,
                fast_output_tokens=200,
                strong_called=True,
                strong_input_tokens=1_000,
                strong_output_tokens=200,
            )
        baseline = cost_tracker.calculate_baseline_sonnet_cost(2_000, 400)
        savings = cost_tracker.calculate_savings(Decimal(str(actual)), baseline)

    assert actual == 0.004084
    assert baseline == Decimal("0.00800000")
    assert savings["savings"] == Decimal("0.00391600")
    assert savings["savings_percentage"] == Decimal("48.95")


def test_zero_baseline_has_finite_savings_percentage():
    result = cost_tracker.calculate_savings(Decimal("0"), Decimal("0"))
    assert result["savings"] == Decimal("0E-8")
    assert result["savings_percentage"] == Decimal("0.00")


def test_missing_usage_or_price_returns_unavailable_costs():
    assert cost_tracker.calculate_cost("fast", None, 10) is None
    with patch.dict(
        cost_tracker.MODEL_PRICING,
        {"fast": {"input_per_mtok": None, "output_per_mtok": 0.12}},
    ):
        result = cost_tracker.calculate_request_costs("fast", 10, 10)
    assert result == {
        "actual_cost": None,
        "sonnet_baseline_cost": cost_tracker.calculate_baseline_sonnet_cost(10, 10),
        "savings": None,
        "savings_percentage": None,
    }


def main():
    test_escalation_cost_and_strong_baseline_include_both_calls()
    test_zero_baseline_has_finite_savings_percentage()
    test_missing_usage_or_price_returns_unavailable_costs()
    print("Cost tracking checks passed.")


if __name__ == "__main__":
    main()
