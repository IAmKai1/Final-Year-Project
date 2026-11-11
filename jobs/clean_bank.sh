# Clean bank on a Kaggle T4: train the clean LoRA models, register them, audit them against each
# other (leave-one-out = the null), fit the calibration, and re-run the compute profile.
source jobs/common.sh  # attach dhareeng/wtt-data-librispeech for fast data
preflight
step setup setup_env
step data get_librispeech dev-clean test-clean train-clean-100
step manifests_devtest python -m data.manifests --config configs/m1_librispeech_manifests.yaml
step manifests_train python -m data.manifests --config configs/librispeech_train_clean_100.yaml
step profile python -m scripts.profile_compute --config configs/m1_profile.yaml
step clean_lora python -m models.clean_lora --config "${BANK_CONFIG:-configs/clean_lora_bank60.yaml}"
step register python -m models.registry add-dir --registry registry/models.csv \
     --root "$(ls -d runs/*clean_lora*/adapters | tail -1)" --role reference
step audit_bank python -m scripts.run_audit --config configs/audit_bank_whisper_tiny.yaml
step calibrate python calibrate.py fit --scores "$(ls -d runs/*audit_bank*/ | tail -1)scores.csv" \
     --out "$OUT/calibration.json" --alpha 0.05
save_outputs
cat "$OUT/steps.txt"
