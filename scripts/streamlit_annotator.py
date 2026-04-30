from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from verifier_guided_reasoning.review import read_review_jsonl, summarize_review_metrics, write_review_jsonl
from verifier_guided_reasoning.schemas import ReviewRecord

DEFAULT_REVIEW_PATH = Path("artifacts/review/review_records.jsonl")
DEFAULT_SAVE_PATH = Path("artifacts/review/annotated_review.jsonl")
ACTIONS = ["accept", "reject", "fix", "needs_second_review"]
ACTION_LABELS = {
    "accept": "Accept",
    "reject": "Reject",
    "fix": "Fix",
    "needs_second_review": "Second review",
}


def load_review_records_from_bytes(content: bytes) -> list[ReviewRecord]:
    records: list[ReviewRecord] = []
    text = content.decode("utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        records.append(ReviewRecord.from_dict(payload))
    return records


def build_demo_records() -> list[ReviewRecord]:
    return [
        ReviewRecord(
            review_id="demo-1",
            prompt_id="demo-1",
            prompt="A baker makes 12 muffins in the morning and 8 muffins in the afternoon. How many muffins does the baker make in total?",
            source_dataset="demo/arithmetic",
            split="demo",
            model_name="demo-model",
            candidate_id="candidate-1",
            raw_output="The baker makes 12 + 8 = <<12+8=20>>20 muffins in total.\n#### 20",
            trace={
                "sample_id": "demo-1",
                "source_dataset": "demo/arithmetic",
                "question": "How many muffins in total?",
                "steps": [
                    {
                        "step_id": "s1",
                        "text": "Add 12 muffins and 8 muffins.",
                        "operation": "arithmetic",
                        "expression": "12 + 8",
                        "computed_value": "20",
                        "depends_on": [],
                    }
                ],
                "final_answer": "20",
                "gold_answer": "20",
                "split": "demo",
                "metadata": {"source_format": "demo"},
            },
            verifier_results=[
                {
                    "sample_id": "demo-1",
                    "step_id": "s1",
                    "status": "pass",
                    "error_type": None,
                    "expected": "20",
                    "observed": "20",
                    "message": "Final answer matches expected output.",
                    "score": 1.0,
                }
            ],
            verifier_pass=True,
            verifier_score=0.97,
            curator_action=None,
            curator_score=None,
            curator_notes=None,
            metadata={"gold_answer": "20"},
        ),
        ReviewRecord(
            review_id="demo-2",
            prompt_id="demo-2",
            prompt="Maya saves $10 on Monday and $5 on Tuesday. How much money has Maya saved altogether?",
            source_dataset="demo/arithmetic",
            split="demo",
            model_name="demo-model",
            candidate_id="candidate-2",
            raw_output="Maya saves 10 + 5 = <<10+5=15>>15 dollars in total.\n#### 15",
            trace={
                "sample_id": "demo-2",
                "source_dataset": "demo/arithmetic",
                "question": "How much money has Maya saved altogether?",
                "steps": [
                    {
                        "step_id": "s1",
                        "text": "Add 10 and 5.",
                        "operation": "arithmetic",
                        "expression": "10 + 5",
                        "computed_value": "15",
                        "depends_on": [],
                    }
                ],
                "final_answer": "15",
                "gold_answer": "15",
                "split": "demo",
                "metadata": {"source_format": "demo"},
            },
            verifier_results=[
                {
                    "sample_id": "demo-2",
                    "step_id": "s1",
                    "status": "pass",
                    "error_type": None,
                    "expected": "15",
                    "observed": "15",
                    "message": "Final answer is correct.",
                    "score": 0.94,
                }
            ],
            verifier_pass=True,
            verifier_score=0.85,
            curator_action=None,
            curator_score=None,
            curator_notes=None,
            metadata={"gold_answer": "15"},
        ),
    ]


def initialize_state() -> None:
    if "review_records" not in st.session_state:
        st.session_state.review_records = []
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "review_source" not in st.session_state:
        st.session_state.review_source = ""
    if "save_path" not in st.session_state:
        st.session_state.save_path = str(DEFAULT_SAVE_PATH)


def load_records_from_path(path: str) -> list[ReviewRecord]:
    return read_review_jsonl(Path(path))


def ensure_current_index() -> None:
    if not st.session_state.review_records:
        st.session_state.current_index = 0
        return
    if st.session_state.current_index >= len(st.session_state.review_records):
        st.session_state.current_index = len(st.session_state.review_records) - 1
    if st.session_state.current_index < 0:
        st.session_state.current_index = 0


def format_action(action: str) -> str:
    return ACTION_LABELS.get(action, action.replace("_", " ").title())


def render_verifier_results(results: list[dict[str, Any]]) -> None:
    if not results:
        st.write("No verifier results available.")
        return
    for index, result in enumerate(results, start=1):
        with st.expander(f"Verifier result {index}: {result.get('status', '')}"):
            st.write("**Step ID:**", result.get("step_id", ""))
            st.write("**Status:**", result.get("status", ""))
            st.write("**Error type:**", result.get("error_type", "none"))
            st.write("**Expected:**", result.get("expected", ""))
            st.write("**Observed:**", result.get("observed", ""))
            st.write("**Message:**", result.get("message", ""))
            st.write("**Score:**", result.get("score", ""))


def render_trace(trace: dict[str, Any]) -> None:
    steps = trace.get("steps", [])
    if not steps:
        st.write("No trace steps available.")
        return
    for step in steps:
        st.markdown(f"**{step.get('step_id', '')}** — {step.get('text', '')}")
        details = []
        if step.get("operation"):
            details.append(f"operation: `{step['operation']}`")
        if step.get("expression") is not None:
            details.append(f"expression: `{step['expression']}`")
        if step.get("computed_value") is not None:
            details.append(f"value: `{step['computed_value']}`")
        if details:
            st.markdown("- " + " · ".join(details))


def render_current_review() -> None:
    review_records = st.session_state.review_records
    index = st.session_state.current_index
    record = review_records[index]
    st.markdown(f"### Reviewing sample {index + 1} of {len(review_records)}")
    st.markdown(
        f"**Prompt ID:** {record.prompt_id}  \
        **Candidate:** {record.candidate_id}  \
        **Model:** {record.model_name}  \
        **Source:** {record.source_dataset}"
    )

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Prompt")
        st.markdown(record.prompt)
        st.markdown("---")
        st.subheader("Trace")
        render_trace(record.trace)
        st.markdown("---")
        st.subheader("Reference")
        st.write("**Gold answer:**", record.metadata.get("gold_answer", record.raw_output))
        st.write("**Final answer:**", record.trace.get("final_answer", ""))

    with right:
        st.subheader("Candidate output")
        st.code(record.raw_output, language="text")
        st.markdown("---")
        st.subheader("Verifier feedback")
        st.write("**Verifier score:**", f"{record.verifier_score:.2f}")
        st.write("**Verifier pass:**", "✅" if record.verifier_pass else "❌")
        render_verifier_results(record.verifier_results)

    st.markdown("---")
    st.subheader("Annotation action")

    default_action = record.curator_action or ("accept" if record.verifier_pass else "reject")
    selected_action = st.radio(
        "Reviewer decision",
        options=ACTIONS,
        format_func=format_action,
        index=ACTIONS.index(default_action) if default_action in ACTIONS else 0,
        horizontal=True,
    )
    record.curator_action = selected_action

    record.curator_score = st.slider(
        "Curator score",
        min_value=0.0,
        max_value=1.0,
        value=record.curator_score if record.curator_score is not None else record.verifier_score,
        step=0.05,
    )

    record.curator_notes = st.text_area(
        "Reviewer notes",
        value=record.curator_notes or "",
        height=180,
        help="Capture why the candidate was accepted, rejected, or needs a second review.",
    ).strip() or None


def main() -> None:
    st.set_page_config(page_title="Verifier Annotator", layout="wide")
    st.title("Verifier-Guided Annotation Console")
    st.markdown(
        "Use this Streamlit app to review verifier-scored candidates in a split prompt/candidate layout. "
        "Navigate samples, compare model output to the prompt, and save curator decisions back to JSONL."
    )

    initialize_state()

    with st.sidebar:
        st.header("Review controls")
        uploaded_file = st.file_uploader("Upload review JSONL", type=["jsonl"])
        review_path = st.text_input("Local review JSONL path", value=str(st.session_state.get("review_source", DEFAULT_REVIEW_PATH)))
        load_button = st.button("Load review records")
        demo_button = st.button("Load demo records")

        st.markdown("---")
        st.subheader("Save output")
        save_path = st.text_input("Save annotated JSONL to", value=st.session_state.save_path)
        if save_path:
            st.session_state.save_path = save_path
        st.markdown("---")
        st.caption(
            "If you do not have a review JSONL file yet, use `generate_review_batch.py` to create one." 
            "Otherwise upload a prepared `.jsonl` to begin annotation."
        )

    if load_button:
        if uploaded_file is not None:
            st.session_state.review_records = load_review_records_from_bytes(uploaded_file.getvalue())
            st.session_state.review_source = uploaded_file.name
            st.session_state.current_index = 0
        elif review_path and Path(review_path).exists():
            st.session_state.review_records = load_records_from_path(review_path)
            st.session_state.review_source = review_path
            st.session_state.current_index = 0
        else:
            st.warning("Upload a `.jsonl` file or provide a valid local review JSONL path.")

    if demo_button:
        st.session_state.review_records = build_demo_records()
        st.session_state.review_source = "demo"
        st.session_state.current_index = 0

    if not st.session_state.review_records:
        st.info("Load reviewer records from a file or demo data to begin annotation.")
        return

    ensure_current_index()

    metrics = summarize_review_metrics(st.session_state.review_records)
    st.sidebar.subheader("Annotation metrics")
    st.sidebar.metric("Samples", len(st.session_state.review_records))
    st.sidebar.metric("Reviewed", f"{int(metrics['num_reviewed'])}/{int(metrics['num_candidates'])}")
    st.sidebar.metric("Acceptance", f"{metrics['acceptance_rate']:.0%}")
    st.sidebar.metric("Disagreement", f"{metrics['curator_verifier_disagreement_rate']:.0%}")

    col_prev, col_index, col_next = st.columns([1, 2, 1])
    if col_prev.button("Previous"):
        st.session_state.current_index = max(0, st.session_state.current_index - 1)
    with col_index:
        position = st.slider(
            "Jump to sample",
            min_value=1,
            max_value=len(st.session_state.review_records),
            value=st.session_state.current_index + 1,
            step=1,
        )
        st.session_state.current_index = position - 1
    if col_next.button("Next"):
        st.session_state.current_index = min(len(st.session_state.review_records) - 1, st.session_state.current_index + 1)

    render_current_review()

    st.markdown("---")
    if st.button("Save annotations"):
        target_path = Path(st.session_state.save_path or DEFAULT_SAVE_PATH)
        write_review_jsonl(st.session_state.review_records, target_path)
        st.success(f"Saved {len(st.session_state.review_records)} review records to {target_path}")
        st.balloons()


if __name__ == "__main__":
    main()
