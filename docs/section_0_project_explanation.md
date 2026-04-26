# Section 0: Project Explanation

This section is a technical orientation for readers who are comfortable with software systems, data pipelines, and basic machine learning, but who are not necessarily specialized in ML research.

The purpose is to explain what this project is really doing, why it matters for data annotation and curation work, and how arithmetic and logic verification fit into an iterative model-improvement loop.

## Table Of Contents

1. [Project Purpose](#1-project-purpose)
2. [Why Verifier-Guided Curation Matters](#2-why-verifier-guided-curation-matters)
3. [System Overview](#3-system-overview)
4. [Core Data Contracts](#4-core-data-contracts)
5. [Arithmetic Verification Path](#5-arithmetic-verification-path)
6. [Logic Extension Path](#6-logic-extension-path)
7. [How This Fits Into The Data Wheel](#7-how-this-fits-into-the-data-wheel)
8. [Human Annotation Workflow](#8-human-annotation-workflow)
9. [Exported Training Artifacts](#9-exported-training-artifacts)
10. [Metrics And Operational Signals](#10-metrics-and-operational-signals)
11. [Reproducibility And Publication Gate](#11-reproducibility-and-publication-gate)
12. [What An Employer Should See](#12-what-an-employer-should-see)
13. [Current Limits And Honest Scope](#13-current-limits-and-honest-scope)

## 1. Project Purpose

At a high level, this project is an implementation of **verifier-guided process supervision**.

Instead of treating model outputs as opaque final answers, the system asks for structured intermediate steps, checks those steps with deterministic rules, and turns the results into data-quality signals.

The objective is not to claim full formal verification of LLM reasoning. The objective is to make data curation measurable and repeatable:

- represent reasoning traces in a consistent schema,
- run automated checks that are transparent and deterministic,
- route candidates to human review with useful diagnostics,
- export high-quality artifacts for supervised fine-tuning and preference learning.

This is exactly the kind of applied pipeline work that matters in data annotation roles: clear rubrics, consistent acceptance criteria, and feedback loops that improve both data quality and model quality over time.

## 2. Why Verifier-Guided Curation Matters

When model outputs are used directly as training data, low-quality examples can reinforce the wrong behavior. Typical failure modes include:

- arithmetic slips in intermediate steps,
- skipped reasoning with unsupported final answers,
- inconsistent labels in logic-style tasks,
- polished language that hides incorrect reasoning.

Verifier-guided curation addresses this by introducing an explicit quality boundary before data is accepted:

1. Parse raw outputs into structured traces.
2. Run deterministic checks.
3. Surface step-level error labels.
4. Ask a reviewer to accept/reject/fix with notes.
5. Export only policy-compliant examples.

The value is practical: reviewers spend less time reading unstructured text and more time making auditable decisions with context.

## 3. System Overview

The project has five major layers:

1. **Schema layer**: dataclasses for trace, step, verifier result, review record, preference pair.
2. **Normalization layer**: dataset-specific parsers that convert rows into `TraceRecord` objects.
3. **Verification layer**: deterministic verifiers (arithmetic and narrow logic extension).
4. **Review/export layer**: curator actions, metrics, and artifact writers.
5. **Training/evaluation layer**: SFT scaffold, benchmark summaries, tracking, and reporting.

The notebook orchestrates these layers, but the logic lives in modules under `src/verifier_guided_reasoning/` so the workflow is scriptable and testable.

## 4. Core Data Contracts

The core record type is `TraceRecord`. It includes:

- `question`: prompt/problem statement,
- `steps`: ordered `StepRecord` list,
- `final_answer` and `gold_answer`,
- `metadata`: source/task-specific context.

A verifier produces `VerifierResult` objects with:

- pass/fail status,
- error type,
- expected vs observed values,
- numeric score.

A curator-facing candidate is wrapped in `ReviewRecord`, which adds:

- raw model output,
- verifier diagnostics,
- curator action (`accept`, `reject`, `fix`, etc.),
- optional notes and reviewer score.

This contract-first approach is important for annotation teams because it standardizes what “evidence” is attached to each decision.

## 5. Arithmetic Verification Path

The arithmetic path verifies multi-step numeric reasoning. It checks things such as:

- expression recomputation consistency,
- missing or non-parseable computed values,
- skipped derivations,
- final answer mismatches,
- unit mismatches in mixed-unit statements.

This gives fine-grained error taxonomy rather than a single pass/fail bit. That taxonomy is useful for annotation policy updates. For example:

- many `sign_error` failures suggests stronger rubric prompts around operation polarity,
- many `skipped_step` failures suggests requiring explicit derivations,
- many `missing_expression` failures suggests parser-template improvements.

## 6. Logic Extension Path

Weeks 7-8 add a narrow logic extension that remains deliberately scoped:

- premises + hypothesis framing,
- deterministic label inference (`entailment`, `contradiction`, `unknown`),
- simple forward-chaining over implication rules,
- separate logic benchmark summary function.

This is intentionally separate from arithmetic reporting. The project does not mix arithmetic accuracy and logic label accuracy into one aggregate score, because each task family has different semantics and failure patterns.

For data curation work, this separation is important: you avoid hiding domain-specific quality issues inside a blended metric.

## 7. How This Fits Into The Data Wheel

A data wheel is an iterative loop where model outputs are used to improve future model behavior through better data and supervision.

In this project, the wheel looks like this:

1. **Seed prompts/tasks** are selected.
2. **Model candidates** are generated (single or multiple per prompt).
3. **Deterministic verification** scores each candidate.
4. **Human review** accepts/rejects/fixes with notes.
5. **Curated datasets** are exported for SFT and preferences.
6. **Model training** runs on curated artifacts.
7. **Evaluation and diagnostics** identify new failure clusters.
8. **Rubric and prompt updates** improve the next curation cycle.

This is a practical model-improvement mechanism because it combines automation with human judgment instead of replacing either one.

## 8. Human Annotation Workflow

The notebook now includes lightweight reviewer controls using `ipywidgets`:

- dropdown label assignment,
- free-text notes,
- score controls,
- preview and save actions,
- immediate metric feedback and popup confirmations.

From a hiring perspective, this matters because it demonstrates:

- annotation UX awareness,
- consistency-oriented decision capture,
- operational feedback loops for reviewers,
- export discipline for downstream training.

The reviewer is not forced to trust the verifier blindly. Curator-verifier disagreement is explicitly measured.

## 9. Exported Training Artifacts

The curation output is split into two artifact families:

1. **SFT dataset**: accepted examples for supervised fine-tuning.
2. **Preference pairs**: chosen vs rejected traces for preference-style training.

This split is useful because different training stages need different formats:

- SFT teaches baseline task behavior and response structure.
- Preference data teaches ranking/selection behavior between alternatives.

Even if only SFT is used initially, preference artifacts preserve future optionality.

## 10. Metrics And Operational Signals

The project tracks both model-facing and operations-facing signals.

Model/data quality signals:

- arithmetic final-answer accuracy,
- arithmetic verifier pass rate,
- logic label accuracy,
- logic verifier pass rate,
- error-class counts.

Curation process signals:

- review acceptance rate,
- rejection rate,
- curator-verifier disagreement rate,
- best-of-N score gain,
- rejection-sampling keep rate.

Together, these show not only whether the model is improving, but whether the annotation process itself is stable and informative.

## 11. Reproducibility And Publication Gate

Before publication, the workflow computes a manifest over required artifacts with:

- file existence,
- byte size,
- SHA256 hash.

A reproducibility gate fails if required artifacts are missing or empty. A dataset card is then generated with:

- overview,
- key metrics,
- artifact manifest,
- release notes and gate outcomes.

This is intentionally conservative. The idea is: **do not publish adapter/dataset claims until artifacts are reproducible and auditable**.

## 12. What An Employer Should See

For a data annotator / data curator hiring audience, this project demonstrates:

- ability to turn abstract quality goals into concrete schemas and rubrics,
- comfort with deterministic validation and failure categorization,
- practical reviewer tooling decisions,
- evidence-driven export and publication discipline,
- communication clarity for mixed audiences (engineering + operations).

In other words, it shows that annotation is treated as a high-signal engineering function, not as a manual afterthought.

## 13. Current Limits And Honest Scope

The project intentionally does **not** claim:

- full formal proof systems,
- broad-domain reasoning verification,
- production-grade RLHF orchestration,
- solved preference optimization.

Current scope is arithmetic-first plus narrow logic extension. This is a strength for portfolio credibility because claims remain verifiable and reproducible.

The realistic near-term path is:

1. strengthen curation coverage,
2. increase reviewer consistency,
3. improve failure-specific guidance,
4. train small reproducible baselines,
5. only then expand into heavier methods (e.g., DPO, symbolic backends).
