from pathlib import Path

from verifier_guided_reasoning.publishing import build_artifact_manifest, reproducibility_gate, write_dataset_card


def test_reproducibility_gate_and_dataset_card(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.jsonl"
    artifact.write_text('{"x": 1}\n', encoding="utf-8")

    manifest = build_artifact_manifest([artifact])
    passed, issues = reproducibility_gate(manifest)

    assert passed is True
    assert issues == []
    assert manifest[0]["sha256"]

    card = write_dataset_card(
        output_path=tmp_path / "dataset_card.md",
        title="Test Card",
        overview="Overview text.",
        metrics={"accuracy": 1.0},
        manifest=manifest,
        release_notes=["All checks passed."],
    )

    contents = card.read_text(encoding="utf-8")
    assert "Test Card" in contents
    assert "accuracy" in contents
    assert "Artifact Manifest" in contents
