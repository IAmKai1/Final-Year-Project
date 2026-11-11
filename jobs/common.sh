# Shared helpers for Kaggle jobs (sourced). REPO and OUT are set by scripts/kaggle_jobs.py.
step() {  # step <name> <command...>: run, log status, keep going on failure
  local name="$1"; shift
  echo "=== [$name] $(date -u +%H:%M:%S) $*"
  local t0=$SECONDS
  if "$@"; then echo "$name ok $((SECONDS - t0))s" >> "$OUT/steps.txt"
  else echo "$name FAILED $((SECONDS - t0))s" >> "$OUT/steps.txt"; fi
}
setup_env() {
  pip install -q jiwer peft safetensors soundfile 2>&1 | tail -2
  pip install -q --no-deps -e "$REPO"
  python - <<'PY'
import torch, transformers
print("torch", torch.__version__, "cuda", torch.cuda.is_available(),
      torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-", "transformers", transformers.__version__)
PY
}
get_librispeech() {  # get_librispeech <subset>...
  mkdir -p data_raw
  for s in "$@"; do
    if [ ! -d "data_raw/LibriSpeech/$s" ]; then
      wget -q -O "data_raw/$s.tar.gz" "https://www.openslr.org/resources/12/$s.tar.gz"
      tar -xzf "data_raw/$s.tar.gz" -C data_raw && rm -f "data_raw/$s.tar.gz"
    fi
  done
}
save_outputs() {
  mkdir -p "$OUT"
  [ -d runs ] && cp -r runs "$OUT/"
  [ -d manifests ] && cp -r manifests "$OUT/"
  [ -d registry ] && cp -r registry "$OUT/"
  pip freeze > "$OUT/pip_freeze.txt"
  nvidia-smi > "$OUT/nvidia_smi.txt" 2>&1 || true
}
