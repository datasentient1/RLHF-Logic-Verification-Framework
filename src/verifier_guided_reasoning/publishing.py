from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def build_artifact_manifest(paths: Iterable[str | Path]) -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    for raw_path in paths:
        path = Path(raw_path)
        exists = path.exists()
        entry = {
            "path": str(path),
            "exists": exists,
            "bytes": path.stat().st_size if exists else 0,
            "sha256": sha256_file(path) if exists else None,
        }
        manifest.append(entry)
    return manifest


def reproducibility_gate(manifest: Iterable[dict[str, object]]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for entry in manifest:
        path = str(entry.get("path"))
        if not entry.get("exists"):
            issues.append(f"Missing artifact: {path}")
            continue
        if int(entry.get("bytes") or 0) <= 0:
            issues.append(f"Empty artifact: {path}")
        if not entry.get("sha256"):
            issues.append(f"Missing hash: {path}")
    return (len(issues) == 0, issues)


def write_dataset_card(
    output_path: str | Path,
    title: str,
    overview: str,
    metrics: dict[str, object],
    manifest: list[dict[str, object]],
    release_notes: list[str] | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    release_notes = release_notes or []

    lines = [
        f"# {title}",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Overview",
        overview,
        "",
        "## Metrics",
    ]
    for key, value in metrics.items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Artifact Manifest"])
    for entry in manifest:
        lines.append(
            f"- `{entry['path']}` | exists={entry['exists']} | bytes={entry['bytes']} | sha256={entry['sha256']}"
        )

    if release_notes:
        lines.extend(["", "## Release Notes"])
        for note in release_notes:
            lines.append(f"- {note}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
