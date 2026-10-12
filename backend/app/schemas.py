"""Validated request and response models used by the HTTP API."""

from typing import Literal

from pydantic import BaseModel, Field


class RequestPayload(BaseModel):
    task_type: Literal["classification", "extraction", "summarisation", "qa"]
    input_text: str = Field(min_length=1)
    categories: list[str] | None = None
    fields: list[str] | None = None
    question: str | None = None
