"""Validated request and response models used by the HTTP API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: Literal["classification", "extraction", "summarisation", "qa"]
    input_text: str = Field(min_length=1, max_length=20_000)
    categories: list[str] | None = Field(default=None, min_length=1, max_length=50)
    fields: list[str] | None = Field(default=None, min_length=1, max_length=50)
    question: str | None = Field(default=None, max_length=5_000)

    @field_validator("input_text", "question")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if value is not None else value

    @field_validator("categories", "fields")
    @classmethod
    def validate_label_lists(cls, values):
        if values is None:
            return values
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 200 for value in normalized):
            raise ValueError("Each item must contain 1 to 200 non-whitespace characters.")
        return normalized

    @model_validator(mode="after")
    def validate_task_fields(self):
        if not self.input_text:
            raise ValueError("input_text cannot be blank.")
        if self.task_type == "classification" and not self.categories:
            raise ValueError("categories are required for classification.")
        if self.task_type == "extraction" and not self.fields:
            raise ValueError("fields are required for extraction.")
        if self.task_type == "qa" and not self.question:
            raise ValueError("question is required for Q&A.")
        combined_length = len(self.input_text) + len(self.question or "")
        combined_length += sum(len(value) for value in (self.categories or []))
        combined_length += sum(len(value) for value in (self.fields or []))
        if combined_length > 25_000:
            raise ValueError("The combined request fields exceed the 25,000 character limit.")
        return self
