# Code Reference

This document is a practical guide to the current Python modules in the project.

It is not API documentation in the formal autodoc sense. The goal is to explain responsibility boundaries so a new contributor can quickly see where logic belongs.

## Package Entry Point

Source package: [`src/verifier_guided_reasoning`](../src/verifier_guided_reasoning)

Public exports are defined in [`__init__.py`](../src/verifier_guided_reasoning/__init__.py).

The most important exported objects are:

- `ArithmeticTraceVerifier`
- `StepRecord`
- `TraceRecord`
- `VerifierResult`
- `PreferencePair`
- `gate_trace_record`
- `summarize_benchmark`
- `run_small_demo`

## `schemas.py`

File: [`src/verifier_guided_reasoning/schemas.py`](../src/verifier_guided_reasoning/schemas.py)

Purpose:

- define the canonical records used across the repo,
- centralize validation logic,
- provide stable serialization behavior.

Key types:

- `SchemaValidationError`
- `StepRecord`
- `TraceRecord`
- `VerifierResult`
- `PreferencePair`
- `QualityGateResult`

Use this module whenever a new dataset transform, verifier, or trainer needs a shared record shape.

## `arithmetic.py`

File: [`src/verifier_guided_reasoning/arithmetic.py`](../src/verifier_guided_reasoning/arithmetic.py)

Purpose:

- implement the deterministic verifier for arithmetic traces,
- safely evaluate arithmetic expressions,
- emit step-level and final-answer diagnostics.

Key pieces:

- `safe_eval_expression(expression, variables=None)`
- `ArithmeticTraceVerifier.verify(trace)`

Current verifier behavior:

- parses arithmetic expressions through a restricted AST walker,
- recomputes the expected numeric value,
- compares expected and observed values with a small tolerance,
- supports step-id references through the `symbol_table`,
- checks simple unit consistency by looking at step text,
- validates that the final answer is both correct and trace-supported.

This is intentionally heuristic and arithmetic-specific. It is not a symbolic proof checker.

## `datasets.py`

File: [`src/verifier_guided_reasoning/datasets.py`](../src/verifier_guided_reasoning/datasets.py)

Purpose:

- transform raw dataset rows into `TraceRecord` objects,
- provide gating logic before traces are accepted,
- read and write JSONL files for the demo pipeline.

Key functions:

- `parse_gsm8k_answer(answer)`
- `normalize_gsm8k_record(row, split='train')`
- `parse_calc_svamp_chain(chain)`
- `normalize_calc_svamp_record(row, split='train')`
- `gate_trace_record(trace, verifier=None)`
- `write_jsonl(records, output_path)`
- `read_trace_jsonl(input_path)`
- `build_demo_rows()`

Design note:

This module is the right home for dataset-specific parsing. Keep verifier logic out of here except for the explicit gate step.

## `evaluation.py`

File: [`src/verifier_guided_reasoning/evaluation.py`](../src/verifier_guided_reasoning/evaluation.py)

Purpose:

- aggregate verifier outputs into benchmark-level summaries,
- compute counts, pass rates, and trace-level diagnostics.

Key functions:

- `summarize_results(results)`
- `summarize_benchmark(traces, verifier=None)`

This is where project-level metrics should grow over time, for example:

- best-of-N uplift,
- verifier pass rate,
- failure-type distributions,
- prompted-vs-SFT comparisons.

## `preferences.py`

File: [`src/verifier_guided_reasoning/preferences.py`](../src/verifier_guided_reasoning/preferences.py)

Purpose:

- define the first layer of verifier-derived preference construction.

Key functions:

- `build_preference_pair(...)`
- `mine_preference_pairs(candidate_groups, min_margin=0.2)`

Current status:

- useful for future DPO preparation,
- not yet integrated into a full training loop.

## `tracking.py`

File: [`src/verifier_guided_reasoning/tracking.py`](../src/verifier_guided_reasoning/tracking.py)

Purpose:

- wrap MLflow behind a simpler project-specific interface,
- keep local development usable when MLflow is not installed.

Key classes:

- `ExperimentTracker`
- `TrackingRun`

Behavior:

- if `mlflow` is importable, the tracker uses it,
- otherwise it writes params, metrics, and JSON artifacts to a local directory.

This is a practical choice for a small portfolio project because it avoids making MLflow installation mandatory for every local read-only workflow.

## `reporting.py`

File: [`src/verifier_guided_reasoning/reporting.py`](../src/verifier_guided_reasoning/reporting.py)

Purpose:

- convert summary dictionaries into JSON and Markdown artifacts.

Key functions:

- `render_markdown_report(summary)`
- `write_report_files(summary, json_path, markdown_path=None)`

This module is intentionally presentation-focused. Metric computation should stay in `evaluation.py`.

## `pipeline.py`

File: [`src/verifier_guided_reasoning/pipeline.py`](../src/verifier_guided_reasoning/pipeline.py)

Purpose:

- provide the smallest end-to-end workflow for the current MVP.

Key functions:

- `load_demo_traces()`
- `run_small_demo(...)`

What `run_small_demo` does:

1. load demo traces or read a JSONL file,
2. summarize verifier behavior on those traces,
3. log params and metrics through the tracker,
4. optionally write JSON and Markdown report artifacts.

## Scripts

### `scripts/prepare_datasets.py`

Purpose:

- build a small JSONL file from demo rows,
- run the dataset quality gate,
- split accepted and rejected records.

### `scripts/run_small_demo.py`

Purpose:

- expose `run_small_demo()` as a CLI entry point.

## Tests

### `tests/test_arithmetic_verifier.py`

Covers:

- numeric consistency,
- unit mismatch detection,
- sign-like arithmetic errors,
- skipped-step detection,
- final-answer mismatch detection.

### `tests/test_dataset_transforms.py`

Covers:

- GSM8K normalization,
- Calc-SVAMP chain parsing,
- acceptance by the quality gate for a valid example.

## Recommended Extension Points

If you keep developing the project, these are the cleanest places to add new logic:

- add new dataset parsers in `datasets.py`,
- add new verifier modules next to `arithmetic.py`,
- extend summary metrics in `evaluation.py`,
- add trainer-specific orchestration in a new module instead of overloading the notebook,
- keep the notebook as an orchestration surface, not the source of truth.
