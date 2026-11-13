# Pre-registration v1, E2 family A: the 60 existing clean whisper-tiny models transcribe the pilot's
# audit pool. No training. Attach dhareeng/wtt-data-librispeech (audio) and dhareeng/wtt-clean-bank60 (adapters).
source jobs/common.sh
preflight
step setup setup_env
step data get_librispeech dev-clean test-clean
ADAPTERS=$(find /kaggle/input -maxdepth 8 -type d -name adapters -path "*clean_lora*" | head -1)
echo "adapters: $ADAPTERS" | tee -a "$OUT/steps.txt"
step pool python -m scripts.pool_transcripts --pool configs/pilot_audit_pool.json --audio-root data_raw/LibriSpeech \
     --parent openai/whisper-tiny --models-dir "$ADAPTERS" --out "$OUT/pool_transcripts_whisper_tiny.json"
save_outputs
cat "$OUT/steps.txt"
