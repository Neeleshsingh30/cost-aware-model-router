"""Offline regression coverage for audit task 6.

Run with ``python -m unittest discover -s tests -p test_task6_coverage.py``.
Every provider interaction is mocked; these tests never make paid API calls.
"""

import csv
import json
import os
import subprocess
import sys
import unittest
from uuid import uuid4
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.core import claude_client, cost_tracker
from backend.app.evaluation import evaluator
from backend.app.schemas import RequestPayload
from backend.app.services import request_service


class TaskSixCoverage(unittest.TestCase):
    def test_all_task_types_and_invalid_empty_oversized_requests(self):
        examples = [
            {"task_type": "classification", "input_text": "Hello", "categories": ["a"]},
            {"task_type": "extraction", "input_text": "Hello", "fields": ["name"]},
            {"task_type": "summarisation", "input_text": "Hello"},
            {"task_type": "qa", "input_text": "Context", "question": "What?"},
        ]
        self.assertEqual([RequestPayload(**item).task_type for item in examples], [
            "classification", "extraction", "summarisation", "qa"
        ])
        for invalid in (
            {"task_type": "unknown", "input_text": "x"},
            {"task_type": "summarisation", "input_text": "  "},
            {"task_type": "summarisation", "input_text": "x" * 20_001},
            {"task_type": "classification", "input_text": "x", "categories": []},
            {"task_type": "extraction", "input_text": "x", "fields": [" "]},
            {"task_type": "qa", "input_text": "context", "question": "  "},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(Exception):
                RequestPayload(**invalid)

    def test_missing_api_key_fails_configuration_import(self):
        env = os.environ.copy()
        env["CHAT_API_KEY"] = ""
        proc = subprocess.run(
            [sys.executable, "-c", "import backend.app.core.claude_client"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CHAT_API_KEY is missing", proc.stderr)

    def test_provider_auth_rate_limit_timeout_and_connection_errors(self):
        failures = (
            ("AuthenticationError", "Provider authentication failed."),
            ("RateLimitError", "The provider rate limit or quota was reached."),
            ("APITimeoutError", "The provider request timed out."),
            ("APIConnectionError", "Could not connect to the model provider."),
        )
        for name, expected in failures:
            with self.subTest(provider_error=name):
                error_type = type(name, (Exception,), {})
                with patch.object(claude_client, name, error_type), patch(
                    "backend.app.core.claude_client.client.messages.create",
                    side_effect=error_type("simulated"),
                ):
                    result = claude_client.call_model("fake-model", "prompt")
                self.assertTrue(result["error"].startswith(expected))

    def test_malformed_response_and_missing_usage_or_price_are_safe(self):
        parsed = __import__(
            "backend.app.core.confidence_evaluator", fromlist=["parse_confidence_response"]
        ).parse_confidence_response("not json")
        self.assertFalse(parsed["valid"])
        self.assertTrue(parsed["needs_escalation"])
        response = SimpleNamespace(
            content=[SimpleNamespace(text="ok")],
            usage=SimpleNamespace(input_tokens=None, output_tokens=2),
        )
        with patch(
            "backend.app.core.claude_client.client.messages.create", return_value=response
        ):
            result = claude_client.call_model("fake-model", "prompt")
        self.assertIsNone(result["input_tokens"])
        self.assertIsNone(result["output_tokens"])
        self.assertIsNone(cost_tracker.calculate_cost("fast", None, 2))
        with patch.dict(
            cost_tracker.MODEL_PRICING,
            {"fast": {"input_per_mtok": None, "output_per_mtok": 1}},
        ):
            self.assertIsNone(cost_tracker.calculate_cost("fast", 1, 2))

    def test_cost_baseline_savings_and_zero_baseline(self):
        with patch.dict(
            cost_tracker.MODEL_PRICING,
            {
                "fast": {"input_per_mtok": 1, "output_per_mtok": 2},
                "strong": {"input_per_mtok": 2, "output_per_mtok": 4},
            },
        ):
            actual = cost_tracker.calculate_cost("fast", 100_000, 100_000)
            baseline = cost_tracker.calculate_baseline_sonnet_cost(100_000, 100_000)
            savings = cost_tracker.calculate_savings(actual, baseline)
            self.assertEqual(str(actual), "0.30000000")
            self.assertEqual(str(baseline), "0.60000000")
            self.assertEqual(str(savings["savings"]), "0.30000000")
            self.assertEqual(str(savings["savings_percentage"]), "50.00")
        zero = cost_tracker.calculate_savings(0, 0)
        self.assertEqual(str(zero["savings_percentage"]), "0.00")

    def test_failed_request_is_persistently_logged(self):
        failed_result = {
            "answer": "", "error": "provider unavailable", "initial_model": "fast",
            "final_model": "fast", "complexity_score": 0.1, "complexity_reasons": [],
            "input_tokens": None, "output_tokens": None, "actual_cost": None,
            "escalated": False, "routing_decision": "fast_model_failed",
        }
        project_root = Path(__file__).resolve().parents[1]
        data_dir = project_root / "data"
        log_path = data_dir / f".task6-routing-{uuid4().hex}.csv"
        try:
            with patch("backend.app.core.logger.DATA_DIR", data_dir), patch(
                "backend.app.core.logger.LOG_FILE", log_path
            ), patch.object(request_service, "route_request", return_value=failed_result):
                payload = RequestPayload(task_type="summarisation", input_text="Test input")
                result = request_service.process_request(payload)
            self.assertEqual(result["request_status"], "failed")
            with log_path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["request_status"], "failed")
            self.assertEqual(rows[0]["routing_decision"], "fast_model_failed")
        finally:
            log_path.unlink(missing_ok=True)

    def test_twenty_heldout_examples_with_mocked_provider_calls(self):
        dataset = evaluator.load_dataset()[:20]
        self.assertEqual(len(dataset), 20)
        for case in dataset:
            expected = case["expected_output"]
            model_text = json.dumps(expected) if case["task_type"] == "extraction" else str(expected)
            with self.subTest(case_id=case["id"]), patch.object(
                evaluator, "call_model", return_value={
                    "text": model_text, "input_tokens": 10, "output_tokens": 5, "error": None
                }
            ), patch.object(
                evaluator, "route_request", return_value={
                    "answer": model_text, "initial_model": evaluator.FAST_MODEL_ID,
                    "final_model": evaluator.FAST_MODEL_ID, "input_tokens": 10,
                    "output_tokens": 5, "actual_cost": 0.0001, "error": None,
                    "escalated": False,
                }
            ):
                baseline = evaluator.evaluate_baseline_case(case, evaluator.FAST_MODEL_ID)
                routed = evaluator.evaluate_router_case(case)
            self.assertIsNone(baseline["error"])
            self.assertEqual(baseline["score"], 1.0)
            self.assertIsNone(routed["error"])
            self.assertEqual(routed["score"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
