# Google Colab Workflow

## 1. Mount Drive

Use a mounted Drive path for both DVC artifacts and MLflow runs so Colab resets do not wipe the project history.

Recommended paths:

- DVC remote path: `/content/drive/MyDrive/rlhf_logic_verification/dvc`
- MLflow path: `/content/drive/MyDrive/rlhf_logic_verification/mlruns`

## 2. Install Dependencies

```python
%pip install -e .[colab,dev]
```

## 3. Initialize DVC In The Notebook Runtime

```bash
!dvc init
!dvc remote add -d colab_drive /content/drive/MyDrive/rlhf_logic_verification/dvc
```

This repo intentionally avoids DVC's direct Google Drive remote as the default first path. Use the mounted filesystem path first.

## 4. Prepare Demo Data

```bash
!python scripts/prepare_datasets.py --demo --output data/processed/demo_arithmetic.jsonl
```

## 5. Run The Demo

```bash
!python scripts/run_small_demo.py \
  --input data/processed/demo_arithmetic.jsonl \
  --output artifacts/eval/demo_summary.json \
  --report-md artifacts/eval/demo_report.md \
  --tracker-root /content/drive/MyDrive/rlhf_logic_verification/mlruns
```

## 6. Move Into LoRA / QLoRA

Once the verifier and accepted trace subset are stable, the notebook can switch from the small demo to SFT preparation and fine-tuning.

Keep the ordering strict:

1. parse raw rows into `TraceRecord`
2. reject schema-invalid traces
3. reject verifier-inconsistent traces
4. export the accepted SFT set
5. fine-tune
6. evaluate prompted baseline vs SFT vs verifier-reranked outputs
