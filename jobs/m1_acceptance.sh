# M1 acceptance + "build now" checks on a Kaggle T4.
source jobs/common.sh
preflight
step setup setup_env
step data get_librispeech dev-clean test-clean
step pytest python -m pytest -q -p no:cacheprovider
step manifests python -m data.manifests --config configs/m1_librispeech_manifests.yaml
step wer_base python -m scripts.run_wer_baseline --config configs/m1_wer_baseline.yaml
step wer_tiny python -m scripts.run_wer_baseline --config configs/m1_wer_baseline_tiny.yaml
step profile python -m scripts.profile_compute --config configs/m1_profile.yaml
step null_audit python -m scripts.run_audit --config configs/audit_null_whisper_base.yaml
save_outputs
cat "$OUT/steps.txt"
