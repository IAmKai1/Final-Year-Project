# Clean LoRA bank smoke test on a Kaggle T4: 3 clean whisper-tiny fine-tunes.
source jobs/common.sh
step setup setup_env
step data get_librispeech dev-clean test-clean train-clean-100
step manifests_devtest python -m data.manifests --config configs/m1_librispeech_manifests.yaml
step manifests_train python -m data.manifests --config configs/librispeech_train_clean_100.yaml
step clean_lora python -m models.clean_lora --config configs/clean_lora_smoke.yaml
save_outputs
cat "$OUT/steps.txt"
