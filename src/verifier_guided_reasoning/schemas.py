from __future__ import annotations

"""Canonical data contracts used across the verifier-guided reasoning project."""

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


class SchemaValidationError(ValueError):
    """Raised when a record does not satisfy the project schema."""


Scalar = str | int | float | None


def _require_nonempty_str(field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _coerce_str_list(field_name: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SchemaValidationError(f"{field_name} must be a list[str]")
    return value


@dataclass(slots=True)
class StepRecord:
    """One structured reasoning step inside a trace."""

    step_id: str
    text: str
    operation: str
    expression: str | None = None
    computed_value: Scalar = None
    depends_on: list[str] = field(default_factory=list)

    def validate(self) -> None:
        self.step_id = _require_nonempty_str("step_id", self.step_id)
        self.text = _require_nonempty_str("text", self.text)
        self.operation = _require_nonempty_str("operation", self.operation)
        if self.expression is not None and not isinstance(self.expression, str):
            raise SchemaValidationError("expression must be a string or None")
        self.depends_on = _coerce_str_list("depends_on", self.depends_on)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StepRecord":
        record = cls(
            step_id=payload.get("step_id", ""),
            text=payload.get("text", ""),
            operation=payload.get("operation", ""),
            expression=payload.get("expression"),
            computed_value=payload.get("computed_value"),
            depends_on=list(payload.get("depends_on", [])),
        )
        record.validate()
        return record


@dataclass(slots=True)
class TraceRecord:
    """A normalized reasoning example with ordered steps and answer fields."""

    sample_id: str
    source_dataset: str
    question: str
    steps: list[StepRecord]
    final_answer: Scalar
    gold_answer: Scalar
    split: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        self.sample_id = _require_nonempty_str("sample_id", self.sample_id)
        self.source_dataset = _require_nonempty_str("source_dataset", self.source_dataset)
        self.question = _require_nonempty_str("question", self.question)
        self.split = _require_nonempty_str("split", self.split)
        if not isinstance(self.steps, list) or not self.steps:
            raise SchemaValidationError("steps must be a non-empty list[StepRecord]")
        self.steps = [step if isinstance(step, StepRecord) else StepRecord.from_dict(step) for step in self.steps]
        for step in self.steps:
            step.validate()
        if not isinstance(self.metadata, dict):
            raise SchemaValidationError("metadata must be a dict")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["steps"] = [step.to_dict() for step in self.steps]
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TraceRecord":
        record = cls(
            sample_id=payload.get("sample_id", ""),
            source_dataset=payload.get("source_dataset", ""),
            question=payload.get("question", ""),
            steps=[StepRecord.from_dict(step) for step in payload.get("steps", [])],
            final_answer=payload.get("final_answer"),
            gold_answer=payload.get("gold_answer"),
            split=payload.get("split", ""),
            metadata=dict(payload.get("metadata", {})),
        )
        record.validate()
        return record


@dataclass(slots=True)
class VerifierResult:
    """One verifier judgment for either a single step or the final answer."""

    sample_id: str
    step_id: str
    status: str
    error_type: str | None
    expected: Scalar
    observed: Scalar
    message: str
    score: float

    def validate(self) -> None:
        self.sample_id = _require_nonempty_str("sample_id", self.sample_id)
        self.step_id = _require_nonempty_str("step_id", self.step_id)
        self.status = _require_nonempty_str("status", self.status)
        self.message = _require_nonempty_str("message", self.message)
        if not isinstance(self.score, (int, float)):
            raise SchemaValidationError("score must be numeric")
        self.score = float(self.score)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(slots=True)
class PreferencePair:
    """Chosen and rejected traces paired for future preference optimization."""

    prompt: str
    chosen_trace: dict[str, Any]
    rejected_trace: dict[str, Any]
    pair_source: str
    verifier_margin: float

    def validate(self) -> None:
        self.prompt = _require_nonempty_str("prompt", self.prompt)
        self.pair_source = _require_nonempty_str("pair_source", self.pair_source)
        if not isinstance(self.chosen_trace, dict) or not isinstance(self.rejected_trace, dict):
            raise SchemaValidationError("chosen_trace and rejected_trace must be dicts")
        if not isinstance(self.verifier_margin, (int, float)):
            raise SchemaValidationError("verifier_margin must be numeric")
        self.verifier_margin = float(self.verifier_margin)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(slots=True)
class QualityGateResult:
    """Admission decision for whether a trace is safe to keep downstream."""

    sample_id: str
    schema_valid: bool
    verifier_agreement: bool
    accepted: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
