from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Mapping

from .schemas import StepRecord, TraceRecord, VerifierResult

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_UNIT_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?)\s*([A-Za-z$%]+)")


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        match = _NUMBER_PATTERN.search(value.replace(",", ""))
        if not match:
            return None
        try:
            return Decimal(match.group(0))
        except InvalidOperation:
            return None
    return None


def _normalize_unit(raw_unit: str) -> str:
    unit = raw_unit.lower().strip()
    if unit == "$":
        return "dollars"
    if unit.endswith("s") and len(unit) > 1:
        unit = unit[:-1]
    return unit


def safe_eval_expression(expression: str, variables: Mapping[str, Decimal] | None = None) -> Decimal:
    variables = variables or {}
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body, variables)


def _eval_node(node: ast.AST, variables: Mapping[str, Decimal]) -> Decimal:
    if isinstance(node, ast.Constant):
        return Decimal(str(node.value))
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise ValueError(f"Unknown symbol in expression: {node.id}")
        return variables[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        result = _BINARY_OPERATORS[type(node.op)](float(left), float(right))
        return Decimal(str(result))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        operand = _eval_node(node.operand, variables)
        result = _UNARY_OPERATORS[type(node.op)](float(operand))
        return Decimal(str(result))
    raise ValueError(f"Unsupported expression node: {ast.dump(node)}")


def _approx_equal(left: Decimal | None, right: Decimal | None, tol: Decimal = Decimal("0.0001")) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) <= tol


def _extract_question_numbers(question: str) -> set[Decimal]:
    values = set()
    for raw_value in _NUMBER_PATTERN.findall(question.replace(",", "")):
        try:
            values.add(Decimal(raw_value))
        except InvalidOperation:
            continue
    return values


def _detect_unit_mismatch(step: StepRecord) -> str | None:
    matches = _UNIT_PATTERN.findall(step.text)
    if len(matches) < 2:
        return None
    units = {_normalize_unit(unit) for _, unit in matches}
    units.discard("%")
    if len(units) > 1:
        return ", ".join(sorted(units))
    return None


def _classify_numeric_error(expression: str, expected: Decimal, observed: Decimal) -> str:
    if "+" in expression:
        numbers = [_to_decimal(number) for number in _NUMBER_PATTERN.findall(expression)]
        if len(numbers) == 2 and numbers[0] is not None and numbers[1] is not None:
            alternate = numbers[0] - numbers[1]
            if _approx_equal(alternate, observed):
                return "sign_error"
    if "-" in expression:
        numbers = [_to_decimal(number) for number in _NUMBER_PATTERN.findall(expression)]
        if len(numbers) == 2 and numbers[0] is not None and numbers[1] is not None:
            alternate = numbers[0] + numbers[1]
            if _approx_equal(alternate, observed):
                return "sign_error"
    return "numeric_inconsistency"


@dataclass(slots=True)
class ArithmeticTraceVerifier:
    """Deterministic verifier for structured arithmetic traces."""

    allow_reference_variables: bool = True

    def verify(self, trace: TraceRecord) -> list[VerifierResult]:
        trace.validate()
        known_values = _extract_question_numbers(trace.question)
        symbol_table: dict[str, Decimal] = {}
        results: list[VerifierResult] = []

        for step in trace.steps:
            step_result = self._verify_step(
                trace=trace,
                step=step,
                known_values=known_values,
                symbol_table=symbol_table,
            )
            results.append(step_result)
            numeric_value = _to_decimal(step.computed_value)
            if numeric_value is not None:
                known_values.add(numeric_value)
                symbol_table[step.step_id] = numeric_value

        results.append(self._verify_final_answer(trace, known_values))
        return results

    def _verify_step(
        self,
        trace: TraceRecord,
        step: StepRecord,
        known_values: set[Decimal],
        symbol_table: dict[str, Decimal],
    ) -> VerifierResult:
        if step.depends_on and any(ref not in symbol_table for ref in step.depends_on):
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id=step.step_id,
                status="fail",
                error_type="missing_dependency",
                expected="all declared dependencies to be available",
                observed="missing dependency",
                message=f"Step {step.step_id} references one or more unknown dependencies.",
                score=0.0,
            )

        if step.expression is None:
            observed = _to_decimal(step.computed_value)
            if observed is None:
                return VerifierResult(
                    sample_id=trace.sample_id,
                    step_id=step.step_id,
                    status="fail",
                    error_type="missing_expression",
                    expected="an explicit arithmetic expression",
                    observed=step.computed_value,
                    message=f"Step {step.step_id} is missing an expression and cannot be recomputed.",
                    score=0.0,
                )
            if observed not in known_values:
                return VerifierResult(
                    sample_id=trace.sample_id,
                    step_id=step.step_id,
                    status="fail",
                    error_type="skipped_step",
                    expected="a derivation from prior values",
                    observed=str(observed),
                    message=f"Step {step.step_id} introduces a new value without a recomputable expression.",
                    score=0.0,
                )
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id=step.step_id,
                status="pass",
                error_type=None,
                expected=str(observed),
                observed=str(observed),
                message=f"Step {step.step_id} reuses a previously established value.",
                score=1.0,
            )

        try:
            expected = safe_eval_expression(step.expression, symbol_table if self.allow_reference_variables else {})
        except Exception as exc:
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id=step.step_id,
                status="fail",
                error_type="invalid_expression",
                expected="a safe arithmetic expression",
                observed=step.expression,
                message=f"Step {step.step_id} could not be evaluated: {exc}",
                score=0.0,
            )

        observed = _to_decimal(step.computed_value)
        if observed is None:
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id=step.step_id,
                status="fail",
                error_type="missing_computed_value",
                expected=str(expected),
                observed=step.computed_value,
                message=f"Step {step.step_id} has an expression but no numeric computed_value.",
                score=0.0,
            )

        mismatch_units = _detect_unit_mismatch(step)
        if mismatch_units:
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id=step.step_id,
                status="fail",
                error_type="unit_mismatch",
                expected="consistent units",
                observed=mismatch_units,
                message=f"Step {step.step_id} mixes incompatible units: {mismatch_units}.",
                score=0.0,
            )

        if not _approx_equal(expected, observed):
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id=step.step_id,
                status="fail",
                error_type=_classify_numeric_error(step.expression, expected, observed),
                expected=str(expected),
                observed=str(observed),
                message=f"Step {step.step_id} does not match the recomputed arithmetic result.",
                score=0.0,
            )

        return VerifierResult(
            sample_id=trace.sample_id,
            step_id=step.step_id,
            status="pass",
            error_type=None,
            expected=str(expected),
            observed=str(observed),
            message=f"Step {step.step_id} is numerically consistent.",
            score=1.0,
        )

    def _verify_final_answer(self, trace: TraceRecord, known_values: set[Decimal]) -> VerifierResult:
        final_answer = _to_decimal(trace.final_answer)
        gold_answer = _to_decimal(trace.gold_answer)

        if final_answer is None:
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id="final",
                status="fail",
                error_type="missing_final_answer",
                expected=trace.gold_answer,
                observed=trace.final_answer,
                message="The trace is missing a parseable final answer.",
                score=0.0,
            )

        if gold_answer is not None and not _approx_equal(final_answer, gold_answer):
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id="final",
                status="fail",
                error_type="final_answer_mismatch",
                expected=str(gold_answer),
                observed=str(final_answer),
                message="The final answer does not match the gold answer.",
                score=0.0,
            )

        if final_answer not in known_values:
            return VerifierResult(
                sample_id=trace.sample_id,
                step_id="final",
                status="fail",
                error_type="skipped_step",
                expected="a final answer derived in prior steps",
                observed=str(final_answer),
                message="The final answer was never established in the reasoning trace.",
                score=0.0,
            )

        return VerifierResult(
            sample_id=trace.sample_id,
            step_id="final",
            status="pass",
            error_type=None,
            expected=str(gold_answer if gold_answer is not None else final_answer),
            observed=str(final_answer),
            message="The final answer matches the verified trace.",
            score=1.0,
        )
