from backend.app.evaluation import evaluator


def test_heldout_dataset_balance_and_first_half_scoring():
    dataset = evaluator.load_dataset()
    assert len(dataset) == 40
    assert len({case["id"] for case in dataset}) == 40
    for task_type in evaluator.TASK_TYPES:
        assert sum(case["task_type"] == task_type for case in dataset) == 10
    for case in dataset[:20]:
        score, correct = evaluator.evaluate_answer(case, case["expected_output"])
        assert score == 1.0
        assert correct is True


def test_classification_and_extraction_scoring_rules():
    classification = {
        "task_type": "classification",
        "expected_output": "Billing",
    }
    assert evaluator.evaluate_answer(classification, " billing ") == (1.0, True)
    assert evaluator.evaluate_answer(classification, "technical") == (0.0, False)

    expected = {"name": "Mira", "phone": None}
    assert evaluator.extraction_score(expected, {"name": "Mira", "phone": None}) == 1.0
    assert evaluator.extraction_score(expected, {"name": "Mira"}) == 0.5
    assert evaluator.extraction_score(expected, {"name": "Mira", "phone": None, "extra": "x"}) < 1.0


def test_failed_or_incomplete_costs_remain_unavailable():
    summary = evaluator.summarize_strategy(
        evaluator.STRATEGY_FAST,
        [
            {
                "score": 1.0,
                "error": None,
                "cost": 0.001,
                "initial_model": evaluator.FAST_MODEL_ID,
                "final_model": evaluator.FAST_MODEL_ID,
            },
            {
                "score": 0.0,
                "error": "provider unavailable",
                "cost": None,
                "initial_model": evaluator.FAST_MODEL_ID,
                "final_model": evaluator.FAST_MODEL_ID,
            },
        ],
    )
    assert summary["successful_requests"] == 1
    assert summary["failed_requests"] == 1
    assert summary["total_cost"] is None
    assert summary["average_cost_per_request"] is None
    assert summary["accuracy"] == 1.0


def main():
    test_heldout_dataset_balance_and_first_half_scoring()
    test_classification_and_extraction_scoring_rules()
    test_failed_or_incomplete_costs_remain_unavailable()
    print("Evaluator checks passed.")


if __name__ == "__main__":
    main()
