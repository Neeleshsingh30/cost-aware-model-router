# =========================================================
# confidence_evaluator.py
# Stage 4: First-stage model confidence evaluation
# =========================================================

import json
import os
import re

from dotenv import load_dotenv

from claude_client import call_model, FAST_MODEL


load_dotenv()


CONFIDENCE_THRESHOLD = float(
    os.getenv("CONFIDENCE_THRESHOLD", "0.75")
)


def build_confidence_prompt(task_prompt: str) -> str:
    """
    Wrap the task-specific prompt with instructions requiring
    structured JSON output and self-reported confidence.
    """

    return f"""
You are the first-stage model in a cost-aware AI model router.

Solve the user's requested task using the instructions below.

IMPORTANT:
You MUST return ONLY valid JSON.
Do not return Markdown.
Do not use ```json or ``` code fences.
Do not add explanations outside the JSON object.

Your response must have exactly these fields:

{{
    "answer": "...",
    "confidence": 0.0,
    "needs_escalation": false,
    "reason": "..."
}}

Field requirements:

1. "answer"
   - Must contain your answer to the requested task.
   - Solve the task normally.

2. "confidence"
   - Must be a number between 0.0 and 1.0.
   - Estimate how reliable your answer is.
   - 1.0 means very high confidence.
   - 0.0 means very low confidence.
   - Do not use confidence merely because the task is easy.

3. "needs_escalation"
   - Must be either true or false.
   - Set it to true if:
     - the task is ambiguous,
     - the task is complex,
     - important information is missing,
     - you are uncertain about the answer,
     - the task requires stronger reasoning,
     - or you believe a stronger model should review the answer.

4. "reason"
   - Briefly explain why you selected the confidence level
     and escalation decision.

Do not invent information.

TASK:

{task_prompt}
"""



def extract_json_object(text: str) -> str:
    """
    Extract a JSON object from model output.

    The preferred behavior is that the model returns JSON only.
    This fallback handles accidental surrounding text safely.
    """

    text = text.strip()

    # Best case: model already returned JSON only.
    if text.startswith("{") and text.endswith("}"):
        return text

    # Fallback: find the first JSON object.
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        return match.group(0)

    raise ValueError("No JSON object found in model response.")



def parse_confidence_response(text: str) -> dict:
    """
    Parse and validate the model's confidence response.

    Invalid or malformed responses are converted into a safe
    escalation result instead of raising an uncontrolled error.
    """

    try:
        json_text = extract_json_object(text)

        data = json.loads(json_text)

    except (json.JSONDecodeError, ValueError, TypeError) as error:
        return {
            "answer": "",
            "confidence": 0.0,
            "needs_escalation": True,
            "reason": f"Malformed JSON response: {error}",
            "valid": False,
        }

    if not isinstance(data, dict):
        return {
            "answer": "",
            "confidence": 0.0,
            "needs_escalation": True,
            "reason": "Model response is not a JSON object.",
            "valid": False,
        }

    required_fields = {
        "answer",
        "confidence",
        "needs_escalation",
        "reason",
    }

    missing_fields = required_fields - data.keys()

    if missing_fields:
        return {
            "answer": data.get("answer", ""),
            "confidence": 0.0,
            "needs_escalation": True,
            "reason": (
                "Missing required fields: "
                + ", ".join(sorted(missing_fields))
            ),
            "valid": False,
        }

    answer = data["answer"]
    confidence = data["confidence"]
    needs_escalation = data["needs_escalation"]
    reason = data["reason"]

    # -----------------------------------------------------
    # Validate answer
    # -----------------------------------------------------

    if not isinstance(answer, str):
        return {
            "answer": "",
            "confidence": 0.0,
            "needs_escalation": True,
            "reason": "Invalid answer type.",
            "valid": False,
        }

    # -----------------------------------------------------
    # Validate confidence
    # -----------------------------------------------------

    if isinstance(confidence, bool) or not isinstance(
        confidence, (int, float)
    ):
        return {
            "answer": answer,
            "confidence": 0.0,
            "needs_escalation": True,
            "reason": "Confidence must be a number between 0 and 1.",
            "valid": False,
        }

    if not 0.0 <= confidence <= 1.0:
        return {
            "answer": answer,
            "confidence": 0.0,
            "needs_escalation": True,
            "reason": "Confidence is outside the allowed range 0 to 1.",
            "valid": False,
        }

    # -----------------------------------------------------
    # Validate escalation flag
    # -----------------------------------------------------

    if not isinstance(needs_escalation, bool):
        return {
            "answer": answer,
            "confidence": confidence,
            "needs_escalation": True,
            "reason": "needs_escalation must be boolean.",
            "valid": False,
        }

    # -----------------------------------------------------
    # Validate reason
    # -----------------------------------------------------

    if not isinstance(reason, str):
        reason = str(reason)

    # -----------------------------------------------------
    # Apply confidence threshold
    # -----------------------------------------------------

    threshold_triggered = confidence < CONFIDENCE_THRESHOLD

    final_escalation = (
        needs_escalation
        or threshold_triggered
    )

    if threshold_triggered:
        final_reason = (
            f"{reason} "
            f"Confidence {confidence:.2f} is below the "
            f"threshold {CONFIDENCE_THRESHOLD:.2f}."
        )
    else:
        final_reason = reason

    return {
        "answer": answer,
        "confidence": confidence,
        "needs_escalation": final_escalation,
        "reason": final_reason,
        "valid": True,
    }



def evaluate_with_fast_model(task_prompt: str) -> dict:
    """
    Send a task to the fast model and evaluate its confidence.

    This function DOES NOT call the strong model.
    It only determines whether escalation would be required.
    """

    prompt = build_confidence_prompt(task_prompt)

    model_result = call_model(
        model=FAST_MODEL,
        prompt=prompt,
    )

    if model_result["error"]:
        return {
            "answer": "",
            "confidence": 0.0,
            "needs_escalation": True,
            "reason": model_result["error"],
            "valid": False,
            "model": model_result["model"],
            "input_tokens": model_result["input_tokens"],
            "output_tokens": model_result["output_tokens"],
            "latency_ms": model_result["latency_ms"],
        }

    parsed_result = parse_confidence_response(
        model_result["text"]
    )

    parsed_result.update(
        {
            "model": model_result["model"],
            "input_tokens": model_result["input_tokens"],
            "output_tokens": model_result["output_tokens"],
            "latency_ms": model_result["latency_ms"],
        }
    )

    return parsed_result