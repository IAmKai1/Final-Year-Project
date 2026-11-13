# Pre-registration v1 (amendment 1), E2 family D: 20 clean wav2vec2-base-960h LoRA models (CTC) + pool transcripts.
PARENT=facebook/wav2vec2-base-960h
TAG=wav2vec2_base
ARCH=ctc
TRAINER=models.clean_lora_ctc
BANK_CONFIG=configs/clean_lora_bank20_wav2vec2_base.yaml
source jobs/e2_bank_common.sh
