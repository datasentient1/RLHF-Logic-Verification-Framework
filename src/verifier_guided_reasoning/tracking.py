from __future__ import annotations

import json
import os
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TrackingRun(AbstractContextManager["TrackingRun"]):
    def __init__(self, tracker: "ExperimentTracker", run_name: str):
        self.tracker = tracker
        self.run_name = run_name
        self.run_dir = tracker.root_dir / tracker.experiment_name / run_name
        self._mlflow_run = None
        if self.tracker.backend != "mlflow":
            self.run_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "TrackingRun":
        if self.tracker.backend == "mlflow":
            import mlflow

            self._mlflow_run = mlflow.start_run(run_name=self.run_name)
        else:
            metadata = {
                "run_name": self.run_name,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "backend": self.tracker.backend,
            }
            (self.run_dir / "run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self.tracker.backend == "mlflow" and self._mlflow_run is not None:
            import mlflow

            mlflow.end_run(status="FAILED" if exc else "FINISHED")
        return None

    def log_params(self, params: dict[str, Any]) -> None:
        if self.tracker.backend == "mlflow":
            import mlflow

            mlflow.log_params(params)
            return
        path = self.run_dir / "params.json"
        path.write_text(json.dumps(params, indent=2, sort_keys=True), encoding="utf-8")

    def log_metrics(self, metrics: dict[str, float]) -> None:
        if self.tracker.backend == "mlflow":
            import mlflow

            mlflow.log_metrics(metrics)
            return
        path = self.run_dir / "metrics.json"
        path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    def log_text(self, name: str, text: str) -> None:
        if self.tracker.backend == "mlflow":
            import mlflow

            mlflow.log_text(text, name)
            return
        (self.run_dir / name).write_text(text, encoding="utf-8")

    def log_json(self, name: str, payload: dict[str, Any]) -> None:
        if self.tracker.backend == "mlflow":
            import mlflow

            mlflow.log_dict(payload, name)
            return
        (self.run_dir / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


class ExperimentTracker:
    """Small MLflow wrapper with a portable local fallback."""

    def __init__(self, root_dir: str | os.PathLike[str] = "mlruns", experiment_name: str = "verifier_guided_reasoning"):
        self.root_dir = Path(root_dir)
        self.experiment_name = experiment_name
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.backend = self._detect_backend()

    def _detect_backend(self) -> str:
        try:
            import mlflow  # noqa: F401
        except ImportError:
            return "local_json"
        return "mlflow"

    def configure(self) -> None:
        if self.backend != "mlflow":
            return
        import mlflow

        tracking_uri = self.root_dir.resolve().as_uri()
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(self.experiment_name)

    def start_run(self, run_name: str) -> TrackingRun:
        self.configure()
        return TrackingRun(self, run_name)
