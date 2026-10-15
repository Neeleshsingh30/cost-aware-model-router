import os
import time

from dotenv import load_dotenv
from anthropic import (
    Anthropic,
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
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
    max_retries=0,
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
            "input_tokens": int | None,
            "output_tokens": int | None,
            "usage_available": bool,
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

        usage = getattr(response, "usage", None)
        input_tokens = _valid_token_count(getattr(usage, "input_tokens", None))
        output_tokens = _valid_token_count(getattr(usage, "output_tokens", None))
        usage_available = input_tokens is not None and output_tokens is not None
        if not usage_available:
            input_tokens = None
            output_tokens = None

        if not text:
            return _error_result(model, "The provider returned an empty response.")

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
            "usage_available": usage_available,
            "model": model,
            "latency_ms": latency_ms,
            "error": None,
        }

    # =====================================================
    # Authentication error
    # =====================================================

    except AuthenticationError:
        return _error_result(model, "Provider authentication failed. Check CHAT_API_KEY.")

    # =====================================================
    # Rate limit error
    # =====================================================

    except RateLimitError:
        return _error_result(model, "The provider rate limit or quota was reached. Check your provider account and try again later.")

    except (PermissionDeniedError, NotFoundError):
        return _error_result(model, "The configured model is unavailable to this API key. Check its model ID and account access.")

    except APITimeoutError:
        return _error_result(model, "The provider request timed out. Try again later.")

    # =====================================================
    # Bad request
    # =====================================================

    except BadRequestError:
        return _error_result(model, "The provider rejected the request. Check the model configuration and request limits.")

    # =====================================================
    # Connection error
    # =====================================================

    except APIConnectionError:
        return _error_result(model, "Could not connect to the model provider. Check internet access and CHAT_BASE_URL.")

    # =====================================================
    # General API error
    # =====================================================

    except APIError:
        return _error_result(model, "The model provider could not complete the request. Try again later.")

    # =====================================================
    # Unexpected error
    # =====================================================

    except Exception:
        return _error_result(model, "The model provider returned an unexpected response. Contact the application administrator if it continues.")


def _valid_token_count(value) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _error_result(model: str, message: str) -> dict:
    return {
        "text": "",
        "input_tokens": None,
        "output_tokens": None,
        "usage_available": False,
        "model": model,
        "latency_ms": None,
        "error": message,
    }
