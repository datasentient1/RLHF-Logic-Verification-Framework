# Data Contracts

This document describes the canonical records used across the verifier-guided reasoning project.

The source of truth is [`src/verifier_guided_reasoning/schemas.py`](../src/verifier_guided_reasoning/schemas.py).

## Why These Contracts Exist

The project is trying to make reasoning artifacts explicit and testable.

Instead of passing around loosely shaped dictionaries, the code normalizes records into a small set of dataclasses with validation methods. That gives the rest of the pipeline a stable interface for:

- dataset normalization,
- schema validation,
- verifier checks,
- report generation,
- later preference-pair mining.

## `StepRecord`

Represents one intermediate reasoning step.

| Field | Type | Description |
|---|---|---|
| `step_id` | `str` | Stable identifier such as `s1` or `s2` |
| `text` | `str` | Human-readable step text |
| `operation` | `str` | Step category, for example `arithmetic`, `calculator`, `explanation` |
| `expression` | `str | None` | Arithmetic expression to recompute |
| `computed_value` | `str | int | float | None` | Claimed numeric output |
| `depends_on` | `list[str]` | Prior step ids this step references |

### Validation behavior

- `step_id`, `text`, and `operation` must be non-empty strings.
- `expression` must be a string or `None`.
- `depends_on` must be a list of strings.

## `TraceRecord`

Represents one normalized reasoning example.

| Field | Type | Description |
|---|---|---|
| `sample_id` | `str` | Unique example id |
| `source_dataset` | `str` | Dataset provenance |
| `question` | `str` | Original prompt or problem |
| `steps` | `list[StepRecord]` | Ordered reasoning trace |
| `final_answer` | `str | int | float | None` | Model or dataset answer |
| `gold_answer` | `str | int | float | None` | Reference answer |
| `split` | `str` | Dataset split such as `train`, `test`, `demo` |
| `metadata` | `dict[str, Any]` | Extra source-specific fields |

### Validation behavior

- `sample_id`, `source_dataset`, `question`, and `split` must be non-empty strings.
- `steps` must be a non-empty list.
- raw dictionaries in `steps` are converted into `StepRecord` objects during validation.
- `metadata` must be a dictionary.

## `VerifierResult`

Represents one verifier judgment.

| Field | Type | Description |
|---|---|---|
| `sample_id` | `str` | Example identifier |
| `step_id` | `str` | Step identifier or `final` |
| `status` | `str` | Usually `pass` or `fail` |
| `error_type` | `str | None` | Failure label if one exists |
| `expected` | `str | int | float | None` | Expected value or condition |
| `observed` | `str | int | float | None` | Observed value from the trace |
| `message` | `str` | Human-readable diagnostic |
| `score` | `float` | Numeric score used in summaries |

## `PreferencePair`

Represents a chosen/rejected pair for later preference optimization.

| Field | Type | Description |
|---|---|---|
| `prompt` | `str` | Original prompt |
| `chosen_trace` | `dict[str, Any]` | Preferred trace payload |
| `rejected_trace` | `dict[str, Any]` | Less preferred trace payload |
| `pair_source` | `str` | How the pair was constructed |
| `verifier_margin` | `float` | Score difference between chosen and rejected traces |

This exists so the project can add verifier-derived preference mining later without redefining the data interface.

## `QualityGateResult`

Represents whether a normalized trace is safe to admit into downstream training or evaluation.

| Field | Type | Description |
|---|---|---|
| `sample_id` | `str` | Example identifier |
| `schema_valid` | `bool` | Whether schema validation passed |
| `verifier_agreement` | `bool` | Whether the verifier found no failures |
| `accepted` | `bool` | Combined admission decision |
| `reasons` | `list[str]` | Failure reasons if rejected |

## Example `TraceRecord`

```json
{
  "sample_id": "demo-good-1",
  "source_dataset": "openai/gsm8k",
  "question": "A baker makes 12 muffins in the morning and 8 muffins in the afternoon. How many muffins does the baker make in total?",
  "steps": [
    {
      "step_id": "s1",
      "text": "The baker makes 12 + 8 = 20 muffins in total.",
      "operation": "arithmetic",
      "expression": "12+8",
      "computed_value": "20",
      "depends_on": []
    }
  ],
  "final_answer": "20",
  "gold_answer": "20",
  "split": "demo",
  "metadata": {
    "source_format": "gsm8k"
  }
}
```

## Serialization Pattern

Each record uses a simple pattern:

- `validate()` ensures the object is internally consistent,
- `to_dict()` returns a JSON-serializable dictionary,
- `from_dict()` reconstructs a validated object when implemented.

That makes the contracts easy to use in scripts, notebooks, and tracked artifacts.
