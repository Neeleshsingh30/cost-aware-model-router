import os
import time
from urllib.parse import urlparse

from dotenv import load_dotenv
from anthropic import (
    Anthropic,
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)


# =========================================================
# Load environment variables
# =========================================================

load_dotenv()


# =========================================================
# Configuration
# =========================================================

CHAT_API_KEY = os.getenv("CHAT_API_KEY")

# IMPORTANT:
# For the Anthropic SDK, do NOT include /v1 here.
# The SDK adds /v1/messages automatically.
CHAT_BASE_URL = os.getenv(
    "CHAT_BASE_URL",
    "https://api.experientiallabs.ai",
)
CHAT_PROVIDER_HOST = urlparse(CHAT_BASE_URL).hostname or CHAT_BASE_URL

FAST_MODEL = os.getenv("FAST_MODEL_ID")
STRONG_MODEL = os.getenv("STRONG_MODEL_ID")

MAX_OUTPUT_TOKENS = int(
    os.getenv("MAX_OUTPUT_TOKENS", "1024")
)


# =========================================================
# Validate configuration
# =========================================================

if not CHAT_API_KEY:
    raise ValueError(
        "CHAT_API_KEY is missing from the .env file."
    )

if not CHAT_BASE_URL:
    raise ValueError(
        "CHAT_BASE_URL is missing from the .env file."
    )

if not FAST_MODEL:
    raise ValueError(
        "FAST_MODEL_ID is missing from the .env file."
    )

if not STRONG_MODEL:
    raise ValueError(
        "STRONG_MODEL_ID is missing from the .env file."
    )


# =========================================================
# Create Anthropic-compatible client
# =========================================================

client = Anthropic(
    api_key=CHAT_API_KEY,
    base_url=CHAT_BASE_URL,
    max_retries=2,
)


# =========================================================
# Reusable model call
# =========================================================

def call_model(
    model: str,
    prompt: str,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> dict:
    """
    Call an Anthropic-compatible model through
    Experiential Labs.

    Parameters
    ----------
    model : str
        Model ID configured in .env.

    prompt : str
        User prompt.

    max_tokens : int
        Maximum number of output tokens.

    Returns
    -------
    dict
        Standardized model response:

        {
            "text": str,
            "input_tokens": int,
            "output_tokens": int,
            "model": str,
            "latency_ms": float | None,
            "error": str | None
        }
    """

    start_time = time.perf_counter()

    try:

        # -------------------------------------------------
        # Anthropic Messages API
        # -------------------------------------------------

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        # -------------------------------------------------
        # Extract text
        # -------------------------------------------------

        text_parts = []

        for block in response.content:

            if hasattr(block, "text"):
                text_parts.append(block.text)

        text = "".join(text_parts)

        # -------------------------------------------------
        # Extract token usage
        # -------------------------------------------------

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # -------------------------------------------------
        # Calculate latency
        # -------------------------------------------------

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        # -------------------------------------------------
        # Return standardized result
        # -------------------------------------------------

        return {
            "text": text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": model,
            "latency_ms": latency_ms,
            "error": None,
        }

    # =====================================================
    # Authentication error
    # =====================================================

    except AuthenticationError:

        return {
            "text": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "model": model,
            "latency_ms": None,
            "error": (
                "Authentication failed. "
                "Check CHAT_API_KEY in .env."
            ),
        }

    # =====================================================
    # Rate limit error
    # =====================================================

    except RateLimitError as error:

        return {
        "text": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "model": model,
        "latency_ms": None,
        "error": (
            f"Rate limit / quota error: {error}"
        ),
    }

    # =====================================================
    # Bad request
    # =====================================================

    except BadRequestError as error:

        return {
            "text": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "model": model,
            "latency_ms": None,
            "error": (
                f"Bad request: {error.message}"
            ),
        }

    # =====================================================
    # Connection error
    # =====================================================

    except APIConnectionError as error:

        transport_error = error
        seen_errors = set()
        while id(transport_error) not in seen_errors:
            seen_errors.add(id(transport_error))
            nested_error = (
                transport_error.__cause__
                or transport_error.__context__
            )
            if nested_error is None:
                break
            transport_error = nested_error

        transport_detail = type(transport_error).__name__

        return {
            "text": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "model": model,
            "latency_ms": None,
            "error": (
                "Could not connect to the model provider at "
                f"{CHAT_PROVIDER_HOST}. Check internet access, proxy settings, "
                "and CHAT_BASE_URL. "
                f"Transport error: {transport_detail}."
            ),
        }

    # =====================================================
    # General API error
    # =====================================================

    except APIError as error:

        return {
            "text": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "model": model,
            "latency_ms": None,
            "error": (
                f"API error: {error.message}"
            ),
        }

    # =====================================================
    # Unexpected error
    # =====================================================

    except Exception as error:

        return {
            "text": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "model": model,
            "latency_ms": None,
            "error": (
                f"Unexpected error: {error}"
            ),
        }
