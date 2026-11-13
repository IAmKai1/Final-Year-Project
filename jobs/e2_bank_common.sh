# Pre-registration v1, E2 families B and C (sourced; SIZE and BANK_CONFIG are set by the wrapper job):
# train a clean LoRA bank for openai/whisper-$SIZE, then every model transcribes the pilot's audit pool.
# Attach dhareeng/wtt-data-librispeech (audio). Clean models only.
source jobs/common.sh
preflight
step setup setup_env
step data get_librispeech dev-clean test-clean train-clean-100
step manifests_devtest python -m data.manifests --config configs/m1_librispeech_manifests.yaml
step manifests_train python -m data.manifests --config configs/librispeech_train_clean_100.yaml
step clean_lora python -m models.clean_lora --config "$BANK_CONFIG"
ADAPTERS=$(ls -d runs/*clean_lora*/adapters | tail -1)
echo "adapters: $ADAPTERS" | tee -a "$OUT/steps.txt"
step pool python -m scripts.pool_transcripts --pool configs/pilot_audit_pool.json --audio-root data_raw/LibriSpeech \
     --parent "openai/whisper-$SIZE" --models-dir "$ADAPTERS" --out "$OUT/pool_transcripts_whisper_$SIZE.json"
save_outputs
cat "$OUT/steps.txt"
