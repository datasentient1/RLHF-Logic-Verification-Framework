from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifier_guided_reasoning.datasets import (
    build_demo_rows,
    gate_trace_record,
    normalize_gsm8k_record,
    write_jsonl,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare demo or lightweight reasoning datasets.")
    parser.add_argument("--output", required=True, help="Where to write the trace JSONL file.")
    parser.add_argument("--demo", action="store_true", help="Use bundled demo rows instead of downloading datasets.")
    args = parser.parse_args()

    rows = build_demo_rows()
    traces = [normalize_gsm8k_record(row, split="demo") for row in rows]
    accepted = []
    rejected = []

    for trace in traces:
        gate = gate_trace_record(trace)
        payload = trace.to_dict()
        payload["quality_gate"] = gate.to_dict()
        if gate.accepted:
            accepted.append(payload)
        else:
            rejected.append(payload)

    write_jsonl(accepted, args.output)
    if rejected:
        rejected_output = args.output.replace(".jsonl", "_rejected.jsonl")
        write_jsonl(rejected, rejected_output)


if __name__ == "__main__":
    main()
