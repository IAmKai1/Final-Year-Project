#!/usr/bin/env bash
# "Build now" checks on a Kaggle/Colab T4 (internet ON), run from the repo root after kaggle_m1.sh:
#   bash scripts/kaggle_build_now.sh
# Runs the full test suite (including the torch tests skipped on CPU-only machines)
# and the null audit of whisper-base against itself.
set -euo pipefail
pip install -q jiwer soundfile peft safetensors
pip install -q -e .
python -m pytest -q
python -m scripts.run_audit --config configs/audit_null_whisper_base.yaml
