# 8-Week Core Roadmap

## Positioning

This project is built as a verifier-guided reasoning system. The public story should emphasize structured reasoning traces, deterministic validation, and data-quality-aware supervision.

## Core Path

### Weeks 1-2

- finalize the trace schema,
- get the arithmetic verifier stable,
- stand up the Colab notebook,
- set up DVC and MLflow paths on mounted Google Drive,
- run the small demo end to end.

### Weeks 3-4

- normalize `Calc-SVAMP` into `TraceRecord` objects,
- build a filtered `GSM8K` structured-trace subset,
- reject rows that fail schema or verifier gates,
- train a LoRA or QLoRA SFT baseline on the accepted arithmetic subset.

### Weeks 5-6

- generate multiple candidate traces per prompt,
- score them with the verifier,
- implement best-of-N reranking or rejection sampling,
- collect failure cases and write short diagnostics for each failure class.

### Weeks 7-8

- add a narrow logic extension,
- keep logic evaluation separate from arithmetic reporting,
- polish the README, notebook, and demo report,
- publish the adapter and dataset card only after the workflow is reproducible.

## Stretch Path

- DPO from verifier-derived preference pairs
- Z3-backed arithmetic or constraint checks
- LeanDojo or minif2f exploration after the public MVP lands
