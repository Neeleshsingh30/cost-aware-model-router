from confidence_evaluator import evaluate_with_fast_model


def main():
    task_prompt = """
    Classify the following customer request into one category:

    Categories:
    - billing
    - technical
    - account
    - sales

    Customer request:
    I was charged twice for the same order.
    """

    result = evaluate_with_fast_model(task_prompt)

    print("=" * 60)
    print("FAST MODEL RESULT")
    print("=" * 60)

    print("Model:", result["model"])
    print("Answer:", result["answer"])
    print("Confidence:", result["confidence"])
    print("Needs escalation:", result["needs_escalation"])
    print("Reason:", result["reason"])
    print("Valid:", result["valid"])
    print("Input tokens:", result["input_tokens"])
    print("Output tokens:", result["output_tokens"])
    print("Latency:", result["latency_ms"])


if __name__ == "__main__":
    main()