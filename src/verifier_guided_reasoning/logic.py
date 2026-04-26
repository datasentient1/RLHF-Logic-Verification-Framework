from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import mean

from .schemas import TraceRecord, VerifierResult

_ALLOWED_LABELS = {"entailment", "contradiction", "unknown"}
_IMPLIES_PATTERN = re.compile(r"^(?:if\s+)?(?P<lhs>.+?)\s*(?:->|=>|implies|then)\s*(?P<rhs>.+)$", re.IGNORECASE)
_WS_PATTERN = re.compile(r"\s+")


def _normalize_statement(statement: str) -> str:
    cleaned = statement.strip().lower()
    cleaned = cleaned.replace("¬", "not ").replace("~", "not ")
    cleaned = cleaned.replace(".", " ").replace(",", " ")
    cleaned = _WS_PATTERN.sub(" ", cleaned).strip()
    return cleaned


def _normalize_label(label: object) -> str | None:
    if label is None:
        return None
    text = str(label).strip().lower()
    return text if text in _ALLOWED_LABELS else None


def _split_implication(statement: str) -> tuple[str, str] | None:
    normalized = _normalize_statement(statement)
    match = _IMPLIES_PATTERN.match(normalized)
    if not match:
        return None
    lhs = _normalize_statement(match.group("lhs"))
    rhs = _normalize_statement(match.group("rhs"))
    if not lhs or not rhs:
        return None
    return lhs, rhs


def _strip_negation(statement: str) -> tuple[bool, str]:
    normalized = _normalize_statement(statement)
    if normalized.startswith("not "):
        return True, _normalize_statement(normalized.removeprefix("not "))
    return False, normalized


def _negate(statement: str) -> str:
    is_negated, base = _strip_negation(statement)
    return base if is_negated else f"not {base}"


def _materialize_facts(premises: list[str]) -> set[str]:
    facts: set[str] = set()
    rules: list[tuple[str, str]] = []

    for premise in premises:
        split = _split_implication(premise)
        if split is None:
            normalized = _normalize_statement(premise)
            if normalized:
                facts.add(normalized)
            continue
        rules.append(split)

    # Tiny forward-chaining closure over Horn-like implications.
    max_iterations = max(1, len(rules) + len(facts) + 2)
    for _ in range(max_iterations):
        changed = False
        for antecedent, consequent in rules:
            if antecedent in facts and consequent not in facts:
                facts.add(consequent)
                changed = True
        if not changed:
            break

    return facts


def infer_logic_label(premises: list[str], hypothesis: str) -> str:
    facts = _materialize_facts(premises)
    normalized_hypothesis = _normalize_statement(hypothesis)
    negated_hypothesis = _negate(normalized_hypothesis)

    has_positive = normalized_hypothesis in facts
    has_negative = negated_hypothesis in facts

    if has_positive and not has_negative:
        return "entailment"
    if has_negative and not has_positive:
        return "contradiction"
    if has_positive and has_negative:
        return "unknown"
    return "unknown"


@dataclass(slots=True)
class LogicTraceVerifier:
    """Deterministic verifier for a narrow propositional entailment task."""

    def verify(self, trace: TraceRecord) -> list[VerifierResult]:
        trace.validate()

        premises = [str(item) for item in trace.metadata.get("premises", []) if str(item).strip()]
        hypothesis = str(trace.metadata.get("hypothesis", "")).strip()
        expected_label = infer_logic_label(premises, hypothesis)

        results: list[VerifierResult] = []
        logic_step_seen = False

        for step in trace.steps:
            if not step.operation.startswith("logic"):
                results.append(
                    VerifierResult(
                        sample_id=trace.sample_id,
                        step_id=step.step_id,
                        status="pass",
                        error_type=None,
                        expected=expected_label,
                        observed=step.computed_value,
                        message=f"Step {step.step_id} is non-logical context and is not scored.",
                        score=1.0,
                    )
                )
                continue

            logic_step_seen = True
            observed_label = _normalize_label(step.computed_value)
            if observed_label is None:
                results.append(
                    VerifierResult(
                        sample_id=trace.sample_id,
                        step_id=step.step_id,
                        status="fail",
                        error_type="invalid_logic_label",
                        expected=expected_label,
                        observed=step.computed_value,
                        message=f"Step {step.step_id} produced an invalid logic label.",
                        score=0.0,
                    )
                )
                continue

            if observed_label != expected_label:
                results.append(
                    VerifierResult(
                        sample_id=trace.sample_id,
                        step_id=step.step_id,
                        status="fail",
                        error_type="logic_label_mismatch",
                        expected=expected_label,
                        observed=observed_label,
                        message=f"Step {step.step_id} logic label does not match premise/hypothesis inference.",
                        score=0.0,
                    )
                )
                continue

            results.append(
                VerifierResult(
                    sample_id=trace.sample_id,
                    step_id=step.step_id,
                    status="pass",
                    error_type=None,
                    expected=expected_label,
                    observed=observed_label,
                    message=f"Step {step.step_id} logic label matches deterministic inference.",
                    score=1.0,
                )
            )

        if not logic_step_seen:
            results.append(
                VerifierResult(
                    sample_id=trace.sample_id,
                    step_id="logic",
                    status="fail",
                    error_type="missing_logic_step",
                    expected=expected_label,
                    observed=None,
                    message="Trace does not contain a logic_label step.",
                    score=0.0,
                )
            )

        results.append(self._verify_final_answer(trace, expected_label))
        return results

    def _verify_final_answer(self, trace: TraceRecord, expected_label: str) -> VerifierResult:
        observed_label = _normalize_label(trace.final_answer)
        gold_label = _normalize_label(trace.gold_answer)

        if observed_label is None:
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id="final",
                status="fail",
                error_type="missing_final_answer",
                expected=gold_label or expected_label,
                observed=trace.final_answer,
                message="Final logic label is missing or invalid.",
                score=0.0,
            )

        if gold_label is not None and observed_label != gold_label:
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id="final",
                status="fail",
                error_type="final_answer_mismatch",
                expected=gold_label,
                observed=observed_label,
                message="Final logic label does not match gold label.",
                score=0.0,
            )

        if observed_label != expected_label:
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id="final",
                status="fail",
                error_type="logic_label_mismatch",
                expected=expected_label,
                observed=observed_label,
                message="Final logic label does not match deterministic inference from premises.",
                score=0.0,
            )

        return VerifierResult(
            sample_id=trace.sample_id,
            step_id="final",
            status="pass",
            error_type=None,
            expected=gold_label or expected_label,
            observed=observed_label,
            message="Final logic label matches deterministic inference.",
            score=1.0,
        )


def mean_logic_score(results: list[VerifierResult]) -> float:
    if not results:
        return 0.0
    return float(mean(result.score for result in results))
