from types import SimpleNamespace
from unittest.mock import patch

from backend.app.core import claude_client, cost_tracker
from backend.app.schemas import RequestPayload


def test_missing_or_malformed_usage_is_unavailable():
    response = SimpleNamespace(
        content=[SimpleNamespace(text="Answer")],
        usage=SimpleNamespace(input_tokens="unknown", output_tokens=4),
    )
    with patch(
        "backend.app.core.claude_client.client.messages.create",
        return_value=response,
    ):
        result = claude_client.call_model("model", "prompt")
    assert result["text"] == "Answer"
    assert result["input_tokens"] is None
    assert result["output_tokens"] is None
    assert result["usage_available"] is False
    assert result["error"] is None


def test_unexpected_provider_exception_does_not_expose_details():
    with patch(
        "backend.app.core.claude_client.client.messages.create",
        side_effect=RuntimeError("private-key-and-upstream-stack"),
    ):
        result = claude_client.call_model("model", "prompt")
    assert result["error"] == (
        "The model provider returned an unexpected response. "
        "Contact the application administrator if it continues."
    )
    assert "private-key" not in result["error"]


def test_missing_price_makes_cost_unavailable():
    with patch.dict(
        cost_tracker.MODEL_PRICING,
        {"fast": {"input_per_mtok": None, "output_per_mtok": 1.0}},
    ):
        assert cost_tracker.calculate_cost("fast", 100, 20) is None
    assert cost_tracker.calculate_cost("fast", None, 20) is None


def test_request_validation_rejects_missing_fields_and_oversized_input():
    try:
        RequestPayload(task_type="classification", input_text="hello")
    except Exception:
        pass
    else:
        raise AssertionError("Classification without categories was accepted")

    try:
        RequestPayload(
            task_type="summarisation",
            input_text="x" * 20_001,
        )
    except Exception:
        pass
    else:
        raise AssertionError("Oversized input was accepted")


def main():
    test_missing_or_malformed_usage_is_unavailable()
    test_unexpected_provider_exception_does_not_expose_details()
    test_missing_price_makes_cost_unavailable()
    test_request_validation_rejects_missing_fields_and_oversized_input()
    print("Provider safety checks passed.")


if __name__ == "__main__":
    main()
