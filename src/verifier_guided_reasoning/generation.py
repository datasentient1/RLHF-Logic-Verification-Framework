from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Callable, Iterable

from .arithmetic import ArithmeticTraceVerifier
from .datasets import parse_gsm8k_answer
from .schemas import StepRecord, TraceRecord, VerifierResult


@dataclass(slots=True)
class GenerationConfig:
    """Configuration for candidate generation from prompts."""

    model_name: str
    num_candidates: int = 3
    max_new_tokens: int = 220
    temperature: float = 0.7
    top_p: float = 0.95
    do_sample: bool = True
    seed: int | None = None


@dataclass(slots=True)
class GeneratedCandidate:
    """One generated answer plus parsed trace and verifier diagnostics."""

    prompt_id: str
    candidate_id: str
    prompt: str
    gold_answer: str | None
    raw_output: str
    trace: TraceRecord
    verifier_results: list[VerifierResult]

    @property
    def verifier_pass(self) -> bool:
        return all(result.status == "pass" for result in self.verifier_results)

    @property
    def verifier_score(self) -> float:
        if not self.verifier_results:
            return 0.0
        return float(mean(result.score for result in self.verifier_results))


def _build_trace_from_generation(
    prompt_id: str,
    prompt: str,
    raw_output: str,
    gold_answer: str | None,
    source_dataset: str,
    split: str,
) -> TraceRecord:
    steps, parsed_final = parse_gsm8k_answer(raw_output)
    if not steps:
        steps = [
            StepRecord(
                step_id="s1",
                text="No parseable arithmetic steps were extracted from model output.",
                operation="unparsed",
                expression=None,
                computed_value=None,
                depends_on=[],
            )
        ]

    final_answer = parsed_final
    return TraceRecord(
        sample_id=prompt_id,
        source_dataset=source_dataset,
        question=prompt,
        steps=steps,
        final_answer=final_answer,
        gold_answer=gold_answer,
        split=split,
        metadata={"source_format": "model_generation"},
    )


def _coerce_gold_answer(raw_answer: Any) -> str | None:
    if raw_answer is None:
        return None
    answer = str(raw_answer).strip()
    if not answer:
        return None
    _, parsed_final = parse_gsm8k_answer(answer)
    return parsed_final or answer


def _strip_prompt_prefix(prompt: str, generated_text: str) -> str:
    cleaned = generated_text.strip()
    if cleaned.startswith(prompt):
        cleaned = cleaned[len(prompt) :].strip()
    return cleaned


def build_hf_generator(config: GenerationConfig) -> Callable[[str], list[str]]:
    """Create a callable that returns N raw candidate outputs for one prompt."""

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    except ImportError as exc:
        raise ImportError(
            "transformers is required for build_hf_generator. Install with the 'colab' extra."
        ) from exc

    if config.seed is not None:
        set_seed(config.seed)

    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(config.model_name)

    def _generate(prompt: str) -> list[str]:
        encoded = tokenizer(prompt, return_tensors="pt")
        generated = model.generate(
            **encoded,
            max_new_tokens=config.max_new_tokens,
            do_sample=config.do_sample,
            temperature=config.temperature,
            top_p=config.top_p,
            num_return_sequences=config.num_candidates,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
        decoded = tokenizer.batch_decode(generated, skip_special_tokens=True)
        return [_strip_prompt_prefix(prompt, text) for text in decoded]

    return _generate


def build_mock_generator() -> Callable[[str], list[str]]:
    """Deterministic fallback generator for demos and testing."""

    def _generate(prompt: str) -> list[str]:
        return [
            (
                f"Solve: {prompt}\n"
                "I combine the numbers from the question in order.\n"
                "The result is <<1+1=2>>2.\n"
                "#### 2"
            ),
            (
                f"Solve: {prompt}\n"
                "I try a subtraction variant first.\n"
                "The result is <<5-3=1>>1.\n"
                "#### 1"
            ),
            (
                f"Solve: {prompt}\n"
                "No arithmetic steps provided.\n"
                "#### 0"
            ),
        ]

    return _generate


def generate_candidates(
    rows: Iterable[dict[str, Any]],
    generator: Callable[[str], list[str]],
    model_name: str,
    split: str = "train",
    verifier: ArithmeticTraceVerifier | None = None,
) -> list[GeneratedCandidate]:
    """Generate, parse, and verify candidate answers for each prompt row."""

    verifier = verifier or ArithmeticTraceVerifier()
    candidates: list[GeneratedCandidate] = []

    for row in rows:
        prompt = str(row.get("question", "")).strip()
        if not prompt:
            continue
        prompt_id = str(row.get("sample_id") or row.get("id") or hash(prompt))
        gold_answer = _coerce_gold_answer(row.get("gold_answer") or row.get("answer"))
        source_dataset = str(row.get("source_dataset") or row.get("dataset") or "generated")

        raw_outputs = generator(prompt)
        for index, raw_output in enumerate(raw_outputs, start=1):
            candidate_id = f"{prompt_id}-c{index}"
            trace = _build_trace_from_generation(
                prompt_id=prompt_id,
                prompt=prompt,
                raw_output=raw_output,
                gold_answer=gold_answer,
                source_dataset=source_dataset,
                split=split,
            )
            results = verifier.verify(trace)
            candidates.append(
                GeneratedCandidate(
                    prompt_id=prompt_id,
                    candidate_id=candidate_id,
                    prompt=prompt,
                    gold_answer=gold_answer,
                    raw_output=raw_output,
                    trace=trace,
                    verifier_results=results,
                )
            )

    return candidates
