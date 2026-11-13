# Pre-registration v1, E2 (sourced; the wrapper job sets SIZE and BANK_CONFIG for a Whisper size, or
# PARENT, TAG, ARCH, TRAINER and BANK_CONFIG for another family): train a clean LoRA bank for the parent,
# then every model transcribes the pilot's audit pool. Attach dhareeng/wtt-data-librispeech (audio).
# Clean models only.
PARENT="${PARENT:-openai/whisper-$SIZE}"
TAG="${TAG:-whisper_$SIZE}"
ARCH="${ARCH:-whisper}"
TRAINER="${TRAINER:-models.clean_lora}"
source jobs/common.sh
preflight
step setup setup_env
step data get_librispeech dev-clean test-clean train-clean-100
step manifests_devtest python -m data.manifests --config configs/m1_librispeech_manifests.yaml
step manifests_train python -m data.manifests --config configs/librispeech_train_clean_100.yaml
step clean_lora python -m "$TRAINER" --config "$BANK_CONFIG"
ADAPTERS=$(ls -d runs/*clean_lora*/adapters | tail -1)
echo "adapters: $ADAPTERS" | tee -a "$OUT/steps.txt"
step pool python -m scripts.pool_transcripts --pool configs/pilot_audit_pool.json --audio-root data_raw/LibriSpeech \
     --arch "$ARCH" --parent "$PARENT" --models-dir "$ADAPTERS" --out "$OUT/pool_transcripts_$TAG.json"
save_outputs
cat "$OUT/steps.txt"
