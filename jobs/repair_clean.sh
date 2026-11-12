# Repair "do no harm" study on a Kaggle T4: GN-FT vs clean fine-tuning on the two parents and three
# clean-bank models. Attach dhareeng/wtt-data-librispeech (audio) and dhareeng/wtt-clean-bank60 (adapters).
source jobs/common.sh
preflight
step setup setup_env
step data get_librispeech dev-clean test-clean train-clean-100
step manifests_devtest python -m data.manifests --config configs/m1_librispeech_manifests.yaml
step manifests_train python -m data.manifests --config configs/librispeech_train_clean_100.yaml
ADAPTERS=$(find /kaggle/input -maxdepth 8 -type d -name adapters -path "*clean_lora*" | head -1)
echo "adapters: $ADAPTERS" | tee -a "$OUT/steps.txt"
step repair_parent_tiny python -m repair.run_repair --config configs/repair_clean_tiny.yaml \
     --checkpoint openai/whisper-tiny --run-name repair_clean_parent_tiny
step repair_parent_base python -m repair.run_repair --config configs/repair_clean_tiny.yaml \
     --checkpoint openai/whisper-base --parent openai/whisper-base --run-name repair_clean_parent_base
for m in clean_tiny_000 clean_tiny_020 clean_tiny_040; do
  step "repair_$m" python -m repair.run_repair --config configs/repair_clean_tiny.yaml \
       --checkpoint "$ADAPTERS/$m" --run-name "repair_clean_$m"
done
save_outputs
cat "$OUT/steps.txt"
