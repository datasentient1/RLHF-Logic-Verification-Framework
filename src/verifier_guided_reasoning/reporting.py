from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Verifier-Guided Reasoning Demo Report",
        "",
        "## Summary",
        f"- Traces evaluated: {summary.get('num_traces', 0)}",
        f"- Final-answer accuracy: {summary.get('final_accuracy', 0.0):.2%}",
        f"- Mean verifier pass rate: {summary.get('pass_rate', 0.0):.2%}",
        "",
        "## Status Counts",
    ]
    for status, count in sorted(summary.get("status_counts", {}).items()):
        lines.append(f"- {status}: {count}")

    lines.extend(["", "## Error Counts"])
    error_counts = summary.get("error_counts", {})
    if error_counts:
        for error_type, count in sorted(error_counts.items()):
            lines.append(f"- {error_type}: {count}")
    else:
        lines.append("- No verifier errors detected.")

    lines.extend(["", "## Trace Diagnostics"])
    for trace in summary.get("traces", []):
        lines.append(
            f"- `{trace['sample_id']}` ({trace['source_dataset']}): final={trace['final_status']}, "
            f"failures={trace['num_failures']}, errors={trace['error_types']}"
        )

    return "\n".join(lines) + "\n"


def write_report_files(summary: dict[str, Any], json_path: str | Path, markdown_path: str | Path | None = None) -> None:
    json_output = Path(json_path)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if markdown_path is not None:
        markdown_output = Path(markdown_path)
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(render_markdown_report(summary), encoding="utf-8")
