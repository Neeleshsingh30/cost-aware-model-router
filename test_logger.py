import csv

from logger import (
    LOG_FILE,
    LOG_FIELDS,
    log_request,
)


def run_test():
    print("Testing request logger...")
    print()

    # =====================================================
    # Sample Request 1
    # =====================================================

    result_1 = log_request(
        task_type="classification",
        input_length=145,
        complexity_score=0.10,
        complexity_reasons=[],
        initial_model="deepseek-v4-flash",
        final_model="deepseek-v4-flash",
        haiku_confidence=0.95,
        escalated=False,
        escalation_reason="",
        input_tokens=120,
        output_tokens=15,
        actual_cost=0.000006,
        sonnet_baseline_cost=0.000255,
        savings=0.000249,
        savings_percentage=97.65,
    )

    print(
        f"Sample request 1 logged: {result_1}"
    )

    # =====================================================
    # Sample Request 2
    # =====================================================

    result_2 = log_request(
        task_type="qa",
        input_length=4200,
        complexity_score=0.82,
        complexity_reasons=[
            "Very long input",
            "Requires reasoning or analysis",
            "Requires comparison or evaluation",
        ],
        initial_model="gpt-6-sol",
        final_model="gpt-6-sol",
        haiku_confidence=None,
        escalated=False,
        escalation_reason="Direct strong-model route due to high complexity.",
        input_tokens=1500,
        output_tokens=250,
        actual_cost=0.005500,
        sonnet_baseline_cost=0.005500,
        savings=0.000000,
        savings_percentage=0.00,
    )

    print(
        f"Sample request 2 logged: {result_2}"
    )

    # =====================================================
    # Verify CSV
    # =====================================================

    print()
    print(f"Log file: {LOG_FILE}")

    if not LOG_FILE.exists():
        raise AssertionError(
            "routing_logs.csv was not created."
        )

    with LOG_FILE.open(
        mode="r",
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        rows = list(reader)

    # Check columns

    if reader.fieldnames != LOG_FIELDS:
        raise AssertionError(
            "CSV columns do not match expected schema."
        )

    # Check at least two new rows exist

    if len(rows) < 2:
        raise AssertionError(
            "Expected at least two log rows."
        )

    print()
    print(
        f"Total log rows currently in CSV: {len(rows)}"
    )

    print()
    print("Latest two logs:")

    for row in rows[-2:]:
        print(
            f"Request ID: {row['request_id']}"
        )
        print(
            f"Task Type: {row['task_type']}"
        )
        print(
            f"Initial Model: {row['initial_model']}"
        )
        print(
            f"Final Model: {row['final_model']}"
        )
        print(
            f"Escalated: {row['escalated']}"
        )
        print(
            f"Actual Cost: {row['actual_cost']}"
        )
        print(
            f"Savings: {row['savings']}"
        )
        print()

    print("PASS: Stage 8 request logging test completed.")


if __name__ == "__main__":
    run_test()