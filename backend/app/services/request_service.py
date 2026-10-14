"""Request orchestration for prompt building, model routing, and accounting."""

from ..core.cost_tracker import calculate_baseline_sonnet_cost, calculate_savings
from ..core.logger import generate_request_id, log_request
from ..core.prompt_builder import build_prompt
from ..core.router import route_request
from ..schemas import RequestPayload


def process_request(payload: RequestPayload) -> dict:
    if not payload.input_text.strip():
        raise ValueError("Input text cannot be blank.")

    prompt = build_prompt(
        task_type=payload.task_type,
        input_text=payload.input_text,
        categories=payload.categories,
        fields=payload.fields,
        question=payload.question,
    )
    result = route_request(text=prompt, task_type=payload.task_type)
    request_id = generate_request_id()
    request_status = "failed" if result.get("error") else "success"

    input_tokens = result.get("input_tokens", 0)
    output_tokens = result.get("output_tokens", 0)
    cost_available = not result.get("error") or bool(input_tokens or output_tokens)

    if not cost_available:
        result.update(
            cost_available=False,
            actual_cost=None,
            sonnet_baseline_cost=None,
            savings=None,
            savings_percentage=None,
        )
        baseline = 0.0
        savings_amount = 0.0
        savings_percentage = 0.0
    else:
        baseline = calculate_baseline_sonnet_cost(input_tokens, output_tokens)
        savings = calculate_savings(result.get("actual_cost", 0), baseline)
        baseline = float(baseline)
        savings_amount = float(savings["savings"])
        savings_percentage = float(savings["savings_percentage"])
        result.update(
            cost_available=True,
            sonnet_baseline_cost=baseline,
            savings=savings_amount,
            savings_percentage=savings_percentage,
        )

    log_request(
        task_type=payload.task_type,
        input_length=len(payload.input_text),
        complexity_score=result.get("complexity_score", 0.0),
        complexity_reasons=result.get("complexity_reasons", []),
        initial_model=result.get("initial_model", ""),
        final_model=result.get("final_model", ""),
        haiku_confidence=result.get("confidence"),
        escalated=result.get("escalated", False),
        escalation_reason=result.get("escalation_reason", ""),
        input_tokens=result.get("input_tokens", 0),
        output_tokens=result.get("output_tokens", 0),
        actual_cost=float(result.get("actual_cost") or 0.0),
        sonnet_baseline_cost=baseline,
        savings=savings_amount,
        savings_percentage=savings_percentage,
        latency_ms=result.get("latency_ms"),
        request_status=request_status,
        request_id=request_id,
    )
    result.update(
        request_id=request_id,
        task_type=payload.task_type,
        request_status=request_status,
        latency_ms=result.get("latency_ms"),
    )
    return result
