# Shared helpers for Kaggle jobs (sourced). REPO and OUT are set by scripts/kaggle_jobs.py.
step() {  # step <name> <command...>: run, log status, keep going on failure
  local name="$1"; shift
  echo "=== [$name] $(date -u +%H:%M:%S) $*"
  local t0=$SECONDS
  if "$@"; then echo "$name ok $((SECONDS - t0))s" >> "$OUT/steps.txt"
  else echo "$name FAILED $((SECONDS - t0))s" >> "$OUT/steps.txt"; fi
}
preflight() {  # stop early (exit 3) if Kaggle gave us no GPU or no internet (unverified phone number)
  local gpu net
  gpu=$(python -c "import torch; print(torch.cuda.is_available())" 2>/dev/null)
  net=$(python -c "import urllib.request; urllib.request.urlopen('https://pypi.org/simple/pip/', timeout=10); print('True')" 2>/dev/null)
  echo "preflight: gpu=${gpu:-False} internet=${net:-False}" | tee "$OUT/preflight.txt"
  if [ "$gpu" != "True" ] || [ "$net" != "True" ]; then
    echo "ABORT: GPU and internet are both required. On Kaggle, verify the account's phone number" | tee -a "$OUT/preflight.txt"
    echo "(Settings > Phone verification); until then notebooks silently run on CPU without internet." | tee -a "$OUT/preflight.txt"
    echo "preflight FAILED" >> "$OUT/steps.txt"
    exit 3
  fi
}
setup_env() {
  pip install -q jiwer peft safetensors soundfile 2>&1 | tail -2
  pip uninstall -y -q torchao 2>&1 | tail -1  # Kaggle image ships an old torchao that makes peft refuse to build LoRA layers
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
      wget -q -O "data_raw/$s.tar.gz" "https://www.openslr.org/resources/12/$s.tar.gz" || return 1
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
