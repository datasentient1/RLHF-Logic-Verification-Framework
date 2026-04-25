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


@dataclass(slots=True)
class ReviewRecord:
    """One candidate model answer prepared for human review."""

    review_id: str
    prompt_id: str
    prompt: str
    source_dataset: str
    split: str
    model_name: str
    candidate_id: str
    raw_output: str
    trace: dict[str, Any]
    verifier_results: list[dict[str, Any]]
    verifier_pass: bool
    verifier_score: float
    curator_action: str | None = None
    curator_score: float | None = None
    curator_notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        self.review_id = _require_nonempty_str("review_id", self.review_id)
        self.prompt_id = _require_nonempty_str("prompt_id", self.prompt_id)
        self.prompt = _require_nonempty_str("prompt", self.prompt)
        self.source_dataset = _require_nonempty_str("source_dataset", self.source_dataset)
        self.split = _require_nonempty_str("split", self.split)
        self.model_name = _require_nonempty_str("model_name", self.model_name)
        self.candidate_id = _require_nonempty_str("candidate_id", self.candidate_id)
        self.raw_output = _require_nonempty_str("raw_output", self.raw_output)
        if not isinstance(self.trace, dict):
            raise SchemaValidationError("trace must be a dict")
        if not isinstance(self.verifier_results, list) or any(not isinstance(item, dict) for item in self.verifier_results):
            raise SchemaValidationError("verifier_results must be a list[dict]")
        if not isinstance(self.verifier_pass, bool):
            raise SchemaValidationError("verifier_pass must be bool")
        if not isinstance(self.verifier_score, (int, float)):
            raise SchemaValidationError("verifier_score must be numeric")
        self.verifier_score = float(self.verifier_score)
        if self.curator_action is not None:
            self.curator_action = _require_nonempty_str("curator_action", self.curator_action)
        if self.curator_score is not None and not isinstance(self.curator_score, (int, float)):
            raise SchemaValidationError("curator_score must be numeric or None")
        if isinstance(self.curator_score, (int, float)):
            self.curator_score = float(self.curator_score)
        if self.curator_notes is not None and not isinstance(self.curator_notes, str):
            raise SchemaValidationError("curator_notes must be a string or None")
        if not isinstance(self.metadata, dict):
            raise SchemaValidationError("metadata must be a dict")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReviewRecord":
        record = cls(
            review_id=payload.get("review_id", ""),
            prompt_id=payload.get("prompt_id", ""),
            prompt=payload.get("prompt", ""),
            source_dataset=payload.get("source_dataset", ""),
            split=payload.get("split", ""),
            model_name=payload.get("model_name", ""),
            candidate_id=payload.get("candidate_id", ""),
            raw_output=payload.get("raw_output", ""),
            trace=dict(payload.get("trace", {})),
            verifier_results=list(payload.get("verifier_results", [])),
            verifier_pass=bool(payload.get("verifier_pass", False)),
            verifier_score=float(payload.get("verifier_score", 0.0)),
            curator_action=payload.get("curator_action"),
            curator_score=payload.get("curator_score"),
            curator_notes=payload.get("curator_notes"),
            metadata=dict(payload.get("metadata", {})),
        )
        record.validate()
        return record
