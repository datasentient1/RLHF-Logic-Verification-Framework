from __future__ import annotations

import json
from html import escape
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
ACTION_HELP = {
    "accept": "Use as training-quality reasoning.",
    "reject": "Exclude from curated data.",
    "fix": "Keep after targeted correction.",
    "needs_second_review": "Escalate for another reviewer.",
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --review-bg: #f6f8fb;
                --review-panel: #ffffff;
                --review-ink: #172033;
                --review-muted: #667085;
                --review-line: #d9e0ea;
                --review-blue: #2251d1;
                --review-green: #067647;
                --review-red: #b42318;
                --review-amber: #b54708;
                --review-purple: #6941c6;
            }

            .stApp {
                background: var(--review-bg);
                color: var(--review-ink);
            }

            .block-container {
                max-width: none;
                padding: 1.05rem 1.35rem 2rem;
            }

            header[data-testid="stHeader"] {
                background: rgba(246, 248, 251, 0.92);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(217, 224, 234, 0.9);
            }

            div[data-testid="stToolbar"] {
                right: 1rem;
            }

            h1, h2, h3 {
                letter-spacing: 0;
            }

            .workbench-topbar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                padding: 0.95rem 1.15rem;
                margin-bottom: 0.85rem;
                background: var(--review-panel);
                border: 1px solid var(--review-line);
                border-radius: 8px;
                box-shadow: 0 10px 28px rgba(23, 32, 51, 0.06);
            }

            .brand-block {
                min-width: 18rem;
            }

            .eyebrow {
                color: var(--review-muted);
                font-size: 0.76rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .page-title {
                margin: 0.1rem 0 0;
                color: var(--review-ink);
                font-size: 1.45rem;
                font-weight: 750;
                line-height: 1.18;
            }

            .session-strip {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                justify-content: flex-end;
                gap: 0.5rem;
            }

            .chip {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                min-height: 1.85rem;
                padding: 0.26rem 0.58rem;
                border: 1px solid var(--review-line);
                border-radius: 999px;
                background: #f9fbff;
                color: #344054;
                font-size: 0.78rem;
                font-weight: 650;
                white-space: nowrap;
            }

            .chip-pass {
                border-color: #abefc6;
                background: #ecfdf3;
                color: var(--review-green);
            }

            .chip-fail {
                border-color: #fecdca;
                background: #fef3f2;
                color: var(--review-red);
            }

            .chip-review {
                border-color: #d6bbfb;
                background: #f4f3ff;
                color: var(--review-purple);
            }

            .metric-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.65rem;
                margin: 0.75rem 0 0.85rem;
            }

            .metric-card {
                padding: 0.82rem 0.9rem;
                background: var(--review-panel);
                border: 1px solid var(--review-line);
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(23, 32, 51, 0.045);
            }

            .metric-label {
                color: var(--review-muted);
                font-size: 0.76rem;
                font-weight: 700;
                text-transform: uppercase;
            }

            .metric-value {
                margin-top: 0.2rem;
                color: var(--review-ink);
                font-size: 1.45rem;
                font-weight: 780;
                line-height: 1;
            }

            .metric-caption {
                margin-top: 0.32rem;
                color: var(--review-muted);
                font-size: 0.78rem;
            }

            .panel {
                padding: 0.95rem;
                margin-bottom: 0.75rem;
                background: var(--review-panel);
                border: 1px solid var(--review-line);
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(23, 32, 51, 0.04);
            }

            .panel-title {
                margin-bottom: 0.55rem;
                color: #344054;
                font-size: 0.78rem;
                font-weight: 760;
                letter-spacing: 0.07em;
                text-transform: uppercase;
            }

            .meta-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.55rem;
                margin-bottom: 0.75rem;
            }

            .meta-cell {
                min-width: 0;
                padding: 0.55rem 0.62rem;
                background: #f9fbff;
                border: 1px solid #edf1f7;
                border-radius: 7px;
            }

            .meta-label {
                color: var(--review-muted);
                font-size: 0.7rem;
                font-weight: 700;
                text-transform: uppercase;
            }

            .meta-value {
                overflow-wrap: anywhere;
                margin-top: 0.15rem;
                color: var(--review-ink);
                font-size: 0.84rem;
                font-weight: 650;
            }

            .sample-card {
                padding: 0.72rem 0.8rem;
                margin-bottom: 0.45rem;
                background: #ffffff;
                border: 1px solid var(--review-line);
                border-left: 4px solid #98a2b3;
                border-radius: 8px;
            }

            .sample-card-active {
                border-left-color: var(--review-blue);
                background: #f5f8ff;
            }

            .sample-title {
                color: var(--review-ink);
                font-size: 0.88rem;
                font-weight: 740;
                overflow-wrap: anywhere;
            }

            .sample-subtitle {
                margin-top: 0.2rem;
                color: var(--review-muted);
                font-size: 0.75rem;
            }

            .rubric-row {
                padding: 0.6rem 0;
                border-bottom: 1px solid #edf1f7;
            }

            .rubric-row:last-child {
                border-bottom: 0;
            }

            .rubric-title {
                color: var(--review-ink);
                font-size: 0.88rem;
                font-weight: 720;
            }

            .rubric-copy {
                color: var(--review-muted);
                font-size: 0.78rem;
                line-height: 1.4;
            }

            .stButton > button {
                background: #ffffff !important;
                border: 1px solid #cfd8e6 !important;
                border-radius: 7px;
                color: var(--review-ink) !important;
                font-weight: 700;
            }

            .stButton > button:hover {
                background: #eef4ff !important;
                border-color: var(--review-blue) !important;
                color: #143f9f !important;
            }

            .stButton > button:focus,
            .stButton > button:active {
                background: #e8efff !important;
                border-color: var(--review-blue) !important;
                color: #143f9f !important;
                box-shadow: 0 0 0 0.16rem rgba(34, 81, 209, 0.16) !important;
            }

            .stButton > button:disabled,
            .stButton > button:disabled:hover {
                background: #f2f4f7 !important;
                border-color: #e4e7ec !important;
                color: #98a2b3 !important;
            }

            .stButton > button p,
            .stButton > button span {
                color: inherit !important;
            }

            [data-testid="stDeployButton"] {
                display: none !important;
            }

            [data-testid="stBaseButton-header"] {
                color: #344054 !important;
            }

            [data-testid="stBaseButton-secondary"],
            [data-testid="stBaseButton-primary"] {
                color: var(--review-ink) !important;
            }

            div[role="radiogroup"] label {
                background: #ffffff !important;
                border: 1px solid #e4e7ec;
                padding: 0.2rem 0.35rem;
                border-radius: 7px;
            }

            div[role="radiogroup"] label:hover {
                background: #f5f8ff !important;
                border-color: #b2c7ff;
            }

            div[role="radiogroup"] label p,
            div[role="radiogroup"] label span {
                color: var(--review-ink) !important;
            }

            div[data-baseweb="tab-list"] button {
                color: #475467 !important;
            }

            div[data-baseweb="tab-list"] button[aria-selected="true"] {
                color: var(--review-blue) !important;
            }

            textarea, input {
                background: #ffffff !important;
                border-radius: 7px !important;
                color: var(--review-ink) !important;
            }

            @media (max-width: 980px) {
                .workbench-topbar {
                    align-items: flex-start;
                    flex-direction: column;
                }

                .session-strip {
                    justify-content: flex-start;
                }

                .metric-grid,
                .meta-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def rerun_app() -> None:
    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun is not None:
        rerun()


def load_records_from_path(path: str) -> list[ReviewRecord]:
    return read_review_jsonl(Path(path))


def autoload_default_records() -> None:
    if st.session_state.review_records or not DEFAULT_REVIEW_PATH.exists():
        return
    try:
        st.session_state.review_records = load_records_from_path(str(DEFAULT_REVIEW_PATH))
        st.session_state.review_source = str(DEFAULT_REVIEW_PATH)
        st.session_state.current_index = 0
    except Exception as exc:
        st.warning(f"Could not auto-load {DEFAULT_REVIEW_PATH}: {exc}")


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


def pct(value: float) -> str:
    return f"{value:.0%}"


def review_status(record: ReviewRecord) -> str:
    if record.curator_action:
        return format_action(record.curator_action)
    return "Unreviewed"


def verifier_chip(record: ReviewRecord) -> str:
    label = "Verifier pass" if record.verifier_pass else "Verifier fail"
    chip_class = "chip-pass" if record.verifier_pass else "chip-fail"
    return f'<span class="chip {chip_class}">{label} · {record.verifier_score:.2f}</span>'


def disagreement_flag(record: ReviewRecord) -> bool:
    if not record.curator_action:
        return False
    curator_accepts = record.curator_action.lower() in {"accept", "fix"}
    return curator_accepts != record.verifier_pass


def render_topbar(metrics: dict[str, float]) -> None:
    records = st.session_state.review_records
    source = escape(st.session_state.review_source or "No source loaded")
    current = st.session_state.current_index + 1 if records else 0
    total = len(records)
    progress = int(metrics["num_reviewed"])
    st.markdown(
        f"""
        <div class="workbench-topbar">
            <div class="brand-block">
                <div class="eyebrow">RLHF Review Workbench</div>
                <div class="page-title">Verifier-Guided Annotation Console</div>
            </div>
            <div class="session-strip">
                <span class="chip">Source · {source}</span>
                <span class="chip">Sample · {current}/{total}</span>
                <span class="chip">Reviewed · {progress}/{int(metrics["num_candidates"])}</span>
                <span class="chip chip-review">Process supervision</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(metrics: dict[str, float]) -> None:
    total = int(metrics["num_candidates"])
    reviewed = int(metrics["num_reviewed"])
    progress = reviewed / total if total else 0.0
    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Queue progress</div>
                <div class="metric-value">{pct(progress)}</div>
                <div class="metric-caption">{reviewed} of {total} candidates reviewed</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Acceptance rate</div>
                <div class="metric-value">{pct(metrics["acceptance_rate"])}</div>
                <div class="metric-caption">Accepted or repairable traces</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Rejection rate</div>
                <div class="metric-value">{pct(metrics["rejection_rate"])}</div>
                <div class="metric-caption">Excluded candidate outputs</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Verifier disagreement</div>
                <div class="metric-value">{pct(metrics["curator_verifier_disagreement_rate"])}</div>
                <div class="metric-caption">Human override signal</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(progress)


def render_loader() -> None:
    with st.expander("Load or save review data", expanded=not st.session_state.review_records):
        input_col, save_col, action_col = st.columns([2.2, 2.2, 1.25])
        with input_col:
            uploaded_file = st.file_uploader("Upload review JSONL", type=["jsonl"])
            review_path = st.text_input(
                "Local review JSONL path",
                value=str(st.session_state.get("review_source", DEFAULT_REVIEW_PATH) or DEFAULT_REVIEW_PATH),
            )
        with save_col:
            save_path = st.text_input("Save annotated JSONL to", value=st.session_state.save_path)
            if save_path:
                st.session_state.save_path = save_path
            st.caption("Records are saved as JSONL with reviewer action, score, and notes preserved.")
        with action_col:
            st.write("")
            load_button = st.button("Load records", use_container_width=True)
            demo_button = st.button("Load demo", use_container_width=True)
            save_button = st.button("Save annotations", use_container_width=True)

        if load_button:
            if uploaded_file is not None:
                st.session_state.review_records = load_review_records_from_bytes(uploaded_file.getvalue())
                st.session_state.review_source = uploaded_file.name
                st.session_state.current_index = 0
                rerun_app()
            elif review_path and Path(review_path).exists():
                st.session_state.review_records = load_records_from_path(review_path)
                st.session_state.review_source = review_path
                st.session_state.current_index = 0
                rerun_app()
            else:
                st.warning("Upload a `.jsonl` file or provide a valid local review JSONL path.")

        if demo_button:
            st.session_state.review_records = build_demo_records()
            st.session_state.review_source = "demo"
            st.session_state.current_index = 0
            rerun_app()

        if save_button:
            save_annotations()


def save_annotations() -> None:
    target_path = Path(st.session_state.save_path or DEFAULT_SAVE_PATH)
    write_review_jsonl(st.session_state.review_records, target_path)
    st.success(f"Saved {len(st.session_state.review_records)} review records to {target_path}")


def render_verifier_results(results: list[dict[str, Any]]) -> None:
    if not results:
        st.write("No verifier results available.")
        return
    for index, result in enumerate(results, start=1):
        status = str(result.get("status", "")).upper()
        score = result.get("score", "")
        with st.expander(f"Check {index}: {status} · score {score}", expanded=index == 1):
            meta_a, meta_b, meta_c = st.columns(3)
            meta_a.metric("Step", result.get("step_id", ""))
            meta_b.metric("Expected", result.get("expected", ""))
            meta_c.metric("Observed", result.get("observed", ""))
            st.write("**Message:**", result.get("message", ""))
            if result.get("error_type"):
                st.warning(f"Error type: {result.get('error_type')}")


def render_trace(trace: dict[str, Any]) -> None:
    steps = trace.get("steps", [])
    if not steps:
        st.write("No trace steps available.")
        return
    for step in steps:
        st.markdown(f"**{step.get('step_id', '')}**: {step.get('text', '')}")
        details = []
        if step.get("operation"):
            details.append(f"operation: `{step['operation']}`")
        if step.get("expression") is not None:
            details.append(f"expression: `{step['expression']}`")
        if step.get("computed_value") is not None:
            details.append(f"value: `{step['computed_value']}`")
        if details:
            st.markdown("- " + " · ".join(details))


def render_queue() -> None:
    records = st.session_state.review_records
    st.markdown('<div class="panel-title">Review queue</div>', unsafe_allow_html=True)
    next_unreviewed = next((i for i, record in enumerate(records) if not record.curator_action), None)
    nav_a, nav_b = st.columns(2)
    if nav_a.button("Previous", use_container_width=True, disabled=st.session_state.current_index == 0):
        st.session_state.current_index = max(0, st.session_state.current_index - 1)
        rerun_app()
    if nav_b.button(
        "Next",
        use_container_width=True,
        disabled=st.session_state.current_index >= len(records) - 1,
    ):
        st.session_state.current_index = min(len(records) - 1, st.session_state.current_index + 1)
        rerun_app()
    if st.button("Next unreviewed", use_container_width=True, disabled=next_unreviewed is None):
        st.session_state.current_index = int(next_unreviewed or 0)
        rerun_app()

    position = st.slider(
        "Jump to sample",
        min_value=1,
        max_value=len(records),
        value=st.session_state.current_index + 1,
        step=1,
    )
    if position - 1 != st.session_state.current_index:
        st.session_state.current_index = position - 1
        rerun_app()

    window_start = max(0, st.session_state.current_index - 4)
    window_end = min(len(records), window_start + 10)
    if window_end - window_start < 10:
        window_start = max(0, window_end - 10)

    for index in range(window_start, window_end):
        record = records[index]
        active_class = " sample-card-active" if index == st.session_state.current_index else ""
        status = review_status(record)
        st.markdown(
            f"""
            <div class="sample-card{active_class}">
                <div class="sample-title">{index + 1}. {escape(record.prompt_id)}</div>
                <div class="sample-subtitle">{escape(status)} · verifier {record.verifier_score:.2f} · {escape(record.model_name)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open", key=f"open-{record.review_id}-{index}", use_container_width=True):
            st.session_state.current_index = index
            rerun_app()


def render_sample_metadata(record: ReviewRecord) -> None:
    disagreement = '<span class="chip chip-review">Human/verifier disagreement</span>' if disagreement_flag(record) else ""
    st.markdown(
        f"""
        <div class="meta-grid">
            <div class="meta-cell">
                <div class="meta-label">Prompt ID</div>
                <div class="meta-value">{escape(record.prompt_id)}</div>
            </div>
            <div class="meta-cell">
                <div class="meta-label">Candidate</div>
                <div class="meta-value">{escape(record.candidate_id)}</div>
            </div>
            <div class="meta-cell">
                <div class="meta-label">Model</div>
                <div class="meta-value">{escape(record.model_name)}</div>
            </div>
            <div class="meta-cell">
                <div class="meta-label">Dataset</div>
                <div class="meta-value">{escape(record.source_dataset)} · {escape(record.split)}</div>
            </div>
        </div>
        <div class="session-strip" style="justify-content:flex-start; margin-bottom: .75rem;">
            {verifier_chip(record)}
            <span class="chip">Reviewer status · {escape(review_status(record))}</span>
            {disagreement}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_rubric() -> None:
    st.markdown(
        """
        <div class="panel-title">Decision rubric</div>
        <div class="rubric-row">
            <div class="rubric-title">Accept</div>
            <div class="rubric-copy">The reasoning is correct, complete, and suitable for downstream SFT or preference construction.</div>
        </div>
        <div class="rubric-row">
            <div class="rubric-title">Fix</div>
            <div class="rubric-copy">The answer is salvageable, but notes should describe the exact correction needed before export.</div>
        </div>
        <div class="rubric-row">
            <div class="rubric-title">Reject</div>
            <div class="rubric-copy">The output has incorrect reasoning, unsupported steps, or quality issues that make it unsafe to keep.</div>
        </div>
        <div class="rubric-row">
            <div class="rubric-title">Second review</div>
            <div class="rubric-copy">Use for ambiguous, policy-sensitive, or verifier-disagreement cases that deserve another pass.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_current_review() -> None:
    review_records = st.session_state.review_records
    index = st.session_state.current_index
    record = review_records[index]
    st.markdown(f'<div class="panel-title">Active sample {index + 1} of {len(review_records)}</div>', unsafe_allow_html=True)
    render_sample_metadata(record)

    prompt_tab, output_tab, trace_tab, verifier_tab, raw_tab = st.tabs(
        ["Prompt", "Candidate output", "Reasoning trace", "Verifier evidence", "Raw record"]
    )

    with prompt_tab:
        prompt_col, reference_col = st.columns([1.45, 1])
        with prompt_col:
            st.markdown("#### User prompt")
            st.markdown(record.prompt)
        with reference_col:
            st.markdown("#### Reference fields")
            st.metric("Gold answer", record.metadata.get("gold_answer", record.trace.get("gold_answer", "")))
            st.metric("Trace final answer", record.trace.get("final_answer", ""))
            if record.trace.get("question"):
                st.write("**Normalized question:**")
                st.write(record.trace.get("question"))

    with output_tab:
        st.markdown("#### Candidate response")
        st.code(record.raw_output, language="text")

    with trace_tab:
        st.markdown("#### Structured reasoning steps")
        render_trace(record.trace)

    with verifier_tab:
        score_col, pass_col, result_col = st.columns([1, 1, 2])
        score_col.metric("Verifier score", f"{record.verifier_score:.2f}")
        pass_col.metric("Verifier gate", "Pass" if record.verifier_pass else "Fail")
        result_col.write("Verifier checks are shown with expected and observed values so the reviewer can audit the automated gate.")
        render_verifier_results(record.verifier_results)

    with raw_tab:
        st.json(record.to_dict())

    st.markdown('<div class="panel-title">Annotation decision</div>', unsafe_allow_html=True)

    default_action = record.curator_action or ("accept" if record.verifier_pass else "reject")
    selected_action = st.radio(
        "Reviewer decision",
        options=ACTIONS,
        format_func=format_action,
        index=ACTIONS.index(default_action) if default_action in ACTIONS else 0,
        horizontal=True,
        key=f"action-{record.review_id}-{index}",
    )
    record.curator_action = selected_action
    st.caption(ACTION_HELP[selected_action])

    record.curator_score = st.slider(
        "Curator score",
        min_value=0.0,
        max_value=1.0,
        value=record.curator_score if record.curator_score is not None else record.verifier_score,
        step=0.05,
        key=f"score-{record.review_id}-{index}",
    )

    record.curator_notes = st.text_area(
        "Reviewer notes",
        value=record.curator_notes or "",
        height=180,
        help="Capture why the candidate was accepted, rejected, or needs a second review.",
        placeholder="Write concise evidence: incorrect step, missing assumption, verifier false positive, or exact repair needed.",
        key=f"notes-{record.review_id}-{index}",
    ).strip() or None

    action_a, action_b, action_c = st.columns([1, 1, 1.2])
    if action_a.button("Save", use_container_width=True, key=f"save-current-{record.review_id}-{index}"):
        save_annotations()
    if action_b.button("Save and next", use_container_width=True, key=f"save-next-{record.review_id}-{index}"):
        save_annotations()
        st.session_state.current_index = min(len(review_records) - 1, index + 1)
        rerun_app()
    if action_c.button(
        "Mark second review and next",
        use_container_width=True,
        key=f"second-review-{record.review_id}-{index}",
    ):
        record.curator_action = "needs_second_review"
        save_annotations()
        st.session_state.current_index = min(len(review_records) - 1, index + 1)
        rerun_app()


def main() -> None:
    st.set_page_config(page_title="Verifier Annotator", layout="wide")
    inject_css()
    initialize_state()
    autoload_default_records()

    if not st.session_state.review_records:
        render_topbar(
            {
                "num_candidates": 0.0,
                "num_reviewed": 0.0,
                "acceptance_rate": 0.0,
                "rejection_rate": 0.0,
                "curator_verifier_disagreement_rate": 0.0,
            }
        )
        render_loader()
        st.info("Load reviewer records from a file or demo data to begin annotation.")
        return

    ensure_current_index()

    metrics = summarize_review_metrics(st.session_state.review_records)
    render_topbar(metrics)
    render_loader()
    render_metric_cards(metrics)

    queue_col, review_col, decision_col = st.columns([1.05, 2.7, 1.15])
    with queue_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_queue()
        st.markdown("</div>", unsafe_allow_html=True)

    with review_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_current_review()
        st.markdown("</div>", unsafe_allow_html=True)

    with decision_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_rubric()
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
