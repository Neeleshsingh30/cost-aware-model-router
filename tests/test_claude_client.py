from claude_client import (
    call_model,
    FAST_MODEL,
    STRONG_MODEL,
)


PROMPT = "Explain machine learning in two sentences."


def main():
    print("Testing FAST_MODEL...")
    print()

    result = call_model(
        model=FAST_MODEL,
        prompt=PROMPT,
        max_tokens=100,
    )

    if result["error"]:
        print("ERROR:")
        print(result["error"])
        return

    print("Model:", result["model"])
    print("Response:")
    print(result["text"])
    print()
    print("Input tokens:", result["input_tokens"])
    print("Output tokens:", result["output_tokens"])
    print("Latency (ms):", result["latency_ms"])


if __name__ == "__main__":
    main()