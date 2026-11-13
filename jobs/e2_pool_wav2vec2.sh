# Pre-registration v1 (amendment 1), E2 family D, transcription only: the 20 clean wav2vec2 models trained by
# dhareeng/wtt-e2-bank-wav2vec2 transcribe the pilot's audit pool. That job's own transcription step ran out of
# GPU memory at batch 32 (wav2vec2 does not truncate 35 s clips); nothing is retrained here.
# Attach dhareeng/wtt-data-librispeech (audio) and dhareeng/wtt-e2-bank-wav2vec2 (adapters).
source jobs/common.sh
preflight
step setup setup_env
step data get_librispeech dev-clean test-clean
ADAPTERS=$(find /kaggle/input -maxdepth 8 -type d -name adapters -path "*clean_lora*wav2vec2*" | head -1)
echo "adapters: $ADAPTERS" | tee -a "$OUT/steps.txt"
step pool python -m scripts.pool_transcripts --arch ctc --batch-size 8 --pool configs/pilot_audit_pool.json \
     --audio-root data_raw/LibriSpeech --parent facebook/wav2vec2-base-960h --models-dir "$ADAPTERS" \
     --out "$OUT/pool_transcripts_wav2vec2_base.json"
save_outputs
cat "$OUT/steps.txt"
