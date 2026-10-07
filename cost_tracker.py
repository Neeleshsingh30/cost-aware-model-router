# =========================================================
# cost_tracker.py
# Stage 7: Token-based cost calculation
# =========================================================

from decimal import Decimal, ROUND_HALF_UP

from config import (
    FAST_INPUT_PRICE_PER_MTOK,
    FAST_OUTPUT_PRICE_PER_MTOK,
    STRONG_INPUT_PRICE_PER_MTOK,
    STRONG_OUTPUT_PRICE_PER_MTOK,
)


# =========================================================
# Model Pricing
# =========================================================
#
# All prices are USD per 1 million tokens.
#
# These values are loaded from config.py / .env.
#
# Do NOT hardcode provider pricing here.
# =========================================================

MODEL_PRICING = {
    "fast": {
        "input_per_mtok": FAST_INPUT_PRICE_PER_MTOK,
        "output_per_mtok": FAST_OUTPUT_PRICE_PER_MTOK,
    },
    "strong": {
        "input_per_mtok": STRONG_INPUT_PRICE_PER_MTOK,
        "output_per_mtok": STRONG_OUTPUT_PRICE_PER_MTOK,
    },
}


TOKENS_PER_MILLION = Decimal("1000000")

MONEY_PLACES = Decimal("0.00000001")


def _to_decimal(value) -> Decimal:
    """
    Convert a numeric value to Decimal safely.
    """

    return Decimal(str(value))


def _validate_tokens(
    input_tokens: int,
    output_tokens: int,
) -> None:
    """
    Validate token counts.
    """

    if isinstance(input_tokens, bool):
        raise TypeError(
            "input_tokens must be an integer."
        )

    if isinstance(output_tokens, bool):
        raise TypeError(
            "output_tokens must be an integer."
        )

    if not isinstance(input_tokens, int):
        raise TypeError(
            "input_tokens must be an integer."
        )

    if not isinstance(output_tokens, int):
        raise TypeError(
            "output_tokens must be an integer."
        )

    if input_tokens < 0:
        raise ValueError(
            "input_tokens cannot be negative."
        )

    if output_tokens < 0:
        raise ValueError(
            "output_tokens cannot be negative."
        )


def _round_money(value: Decimal) -> Decimal:
    """
    Round monetary values to 8 decimal places.
    """

    return value.quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    """
    Calculate estimated model cost in USD.

    model:
        "fast" or "strong"

    Prices are USD per 1 million tokens.
    """

    _validate_tokens(
        input_tokens,
        output_tokens,
    )

    if model not in MODEL_PRICING:
        raise ValueError(
            f"Unknown pricing model: {model}. "
            f"Available models: "
            f"{', '.join(MODEL_PRICING.keys())}"
        )

    pricing = MODEL_PRICING[model]

    input_price = _to_decimal(
        pricing["input_per_mtok"]
    )

    output_price = _to_decimal(
        pricing["output_per_mtok"]
    )

    input_cost = (
        Decimal(input_tokens)
        / TOKENS_PER_MILLION
        * input_price
    )

    output_cost = (
        Decimal(output_tokens)
        / TOKENS_PER_MILLION
        * output_price
    )

    total_cost = input_cost + output_cost

    return _round_money(total_cost)


def calculate_baseline_sonnet_cost(
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    """
    Backward-compatible function name.

    IMPORTANT:
    The actual project baseline is the configured STRONG
    model, currently gpt-6-sol.

    This function estimates what the same token usage
    would cost if the STRONG model handled the request.
    """

    return calculate_cost(
        model="strong",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def calculate_savings(
    actual_cost: Decimal,
    sonnet_baseline_cost: Decimal,
) -> dict:
    """
    Calculate savings against the strong-model baseline.

    savings =
        baseline_cost - actual_cost

    savings_percentage =
        savings / baseline_cost * 100

    Negative savings are allowed.
    """

    actual_cost = _to_decimal(actual_cost)

    baseline_cost = _to_decimal(
        sonnet_baseline_cost
    )

    savings = (
        baseline_cost
        - actual_cost
    )

    if baseline_cost == Decimal("0"):
        savings_percentage = Decimal("0")
    else:
        savings_percentage = (
            savings
            / baseline_cost
            * Decimal("100")
        )

    return {
        "savings": _round_money(savings),
        "savings_percentage": (
            savings_percentage.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        ),
    }


def calculate_request_costs(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> dict:
    """
    Calculate all cost metrics for one request.

    Returns:

        actual_cost
        sonnet_baseline_cost
        savings
        savings_percentage
    """

    actual_cost = calculate_cost(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    baseline_cost = calculate_baseline_sonnet_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    savings_result = calculate_savings(
        actual_cost=actual_cost,
        sonnet_baseline_cost=baseline_cost,
    )

    return {
        "actual_cost": actual_cost,
        "sonnet_baseline_cost": baseline_cost,
        "savings": savings_result["savings"],
        "savings_percentage": (
            savings_result["savings_percentage"]
        ),
    }