import os
from dotenv import load_dotenv


load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise ValueError(
            f"Required environment variable '{name}' is missing."
        )

    return value


def get_float_env(name: str) -> float:
    value = get_required_env(name)

    try:
        return float(value)
    except ValueError:
        raise ValueError(
            f"Environment variable '{name}' must be a number."
        )


def get_int_env(name: str) -> int:
    value = get_required_env(name)

    try:
        return int(value)
    except ValueError:
        raise ValueError(
            f"Environment variable '{name}' must be an integer."
        )


# Experiential Labs
CHAT_API_KEY = get_required_env("CHAT_API_KEY")
CHAT_BASE_URL = get_required_env("CHAT_BASE_URL")

# Models
FAST_MODEL_ID = get_required_env("FAST_MODEL_ID")
STRONG_MODEL_ID = get_required_env("STRONG_MODEL_ID")

# Pricing
FAST_INPUT_PRICE_PER_MTOK = get_float_env(
    "FAST_INPUT_PRICE_PER_MTOK"
)

FAST_OUTPUT_PRICE_PER_MTOK = get_float_env(
    "FAST_OUTPUT_PRICE_PER_MTOK"
)

STRONG_INPUT_PRICE_PER_MTOK = get_float_env(
    "STRONG_INPUT_PRICE_PER_MTOK"
)

STRONG_OUTPUT_PRICE_PER_MTOK = get_float_env(
    "STRONG_OUTPUT_PRICE_PER_MTOK"
)

# Router thresholds
CONFIDENCE_THRESHOLD = get_float_env(
    "CONFIDENCE_THRESHOLD"
)

COMPLEXITY_THRESHOLD = get_float_env(
    "COMPLEXITY_THRESHOLD"
)

# Generation
MAX_OUTPUT_TOKENS = get_int_env(
    "MAX_OUTPUT_TOKENS"
)


def print_config():
    print("Configuration loaded successfully.")
    print()

    print(f"CHAT_BASE_URL: {CHAT_BASE_URL}")
    print(f"FAST_MODEL_ID: {FAST_MODEL_ID}")
    print(f"STRONG_MODEL_ID: {STRONG_MODEL_ID}")

    print()

    print(
        f"FAST_INPUT_PRICE_PER_MTOK: "
        f"{FAST_INPUT_PRICE_PER_MTOK}"
    )

    print(
        f"FAST_OUTPUT_PRICE_PER_MTOK: "
        f"{FAST_OUTPUT_PRICE_PER_MTOK}"
    )

    print(
        f"STRONG_INPUT_PRICE_PER_MTOK: "
        f"{STRONG_INPUT_PRICE_PER_MTOK}"
    )

    print(
        f"STRONG_OUTPUT_PRICE_PER_MTOK: "
        f"{STRONG_OUTPUT_PRICE_PER_MTOK}"
    )

    print()

    print(
        f"CONFIDENCE_THRESHOLD: "
        f"{CONFIDENCE_THRESHOLD}"
    )

    print(
        f"COMPLEXITY_THRESHOLD: "
        f"{COMPLEXITY_THRESHOLD}"
    )

    print(
        f"MAX_OUTPUT_TOKENS: "
        f"{MAX_OUTPUT_TOKENS}"
    )

    print()

    print("CHAT_API_KEY: ****MASKED****")


if __name__ == "__main__":
    try:
        print_config()
    except ValueError as error:
        print(f"Configuration Error: {error}")