# Model families on a Kaggle T4: does the auditor's machinery work beyond Whisper-tiny/base?
# WER on the M1 clips + a null audit (parent vs itself) for whisper-small, distil-small.en and
# wav2vec2-base-960h (CTC), plus a whisper-tiny null. Attach dhareeng/wtt-data-librispeech for the audio.
source jobs/common.sh
preflight
step setup setup_env
step data get_librispeech dev-clean test-clean
step pytest python -m pytest -q -p no:cacheprovider
step manifests python -m data.manifests --config configs/m1_librispeech_manifests.yaml
for f in whisper_small distil_small_en wav2vec2_base_960h; do
  step "wer_$f" python -m scripts.run_wer_baseline --config "configs/families/wer_$f.yaml"
done
for f in wav2vec2_base_960h distil_small_en whisper_tiny whisper_small; do
  step "null_$f" python -m scripts.run_audit --config "configs/families/audit_null_$f.yaml"
done
save_outputs
cat "$OUT/steps.txt"
