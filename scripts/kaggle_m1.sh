#!/usr/bin/env bash
# M1 acceptance on a Kaggle/Colab T4 (internet ON). Run from the repo root:
#   bash scripts/kaggle_m1.sh
# Downloads ~700 MB (LibriSpeech dev-clean + test-clean) and ~0.4 GB of Whisper weights.
set -euo pipefail

pip install -q jiwer soundfile peft
pip install -q -e .

mkdir -p data_raw
for s in dev-clean test-clean; do
  if [ ! -d "data_raw/LibriSpeech/$s" ]; then
    [ -f "data_raw/$s.tar.gz" ] || wget -q -O "data_raw/$s.tar.gz" "https://www.openslr.org/resources/12/$s.tar.gz"
    tar -xzf "data_raw/$s.tar.gz" -C data_raw
  fi
done

python -m pytest -q
python -m data.manifests --config configs/m1_librispeech_manifests.yaml
python -m scripts.run_wer_baseline --config configs/m1_wer_baseline.yaml
python -m scripts.profile_compute --config configs/m1_profile.yaml
