#!/usr/bin/env bash
# Calibration batch: build the benign null distribution the pilot never measured.
#
# Idempotent - every stage is skipped if its output already exists, so the script can be
# re-run after an interruption and will pick up where it stopped.
# Target population: 5 backdoored vs 10 benign.
set -u
cd "$(dirname "$0")"
L=../log_6_calibration.txt
touch $L

while [ "$(grep -c '^saved' ../log_5_repair.txt 2>/dev/null || echo 0)" -lt 6 ]; do
  echo "[$(date +%H:%M)] waiting for the repair sweep" | tee -a $L; sleep 60
done

if [ ! -f ../repair_results.json ]; then
  echo "[$(date +%H:%M)] evaluating repaired models" | tee -a $L
  python 06_eval_repair.py backdoor_s0 backdoor_s0__fta0 backdoor_s0__gnfta0.5 backdoor_s0__gnfta1 \
         backdoor_s1 backdoor_s1__fta0 backdoor_s1__gnfta0.5 backdoor_s1__gnfta1 2>&1 | grep -v "it/s" | tee -a $L
fi

# interleaved so a partial run still leaves a usable mix of both classes
for job in "backdoor 2 1.0" "benign 2 1.0" "benign 3 0.8" "backdoor 3 1.0" "benign 4 0.6" \
           "benign 5 1.0" "backdoor 4 1.0" "benign 6 0.8" "benign 7 0.6" "benign 8 1.0" "benign 9 0.8"; do
  set -- $job
  if [ "$3" = "1.0" ]; then d="../models/$1_s$2"; else d="../models/$1_s$2f$3"; fi
  if [ -f "$d/config.json" ]; then echo "[$(date +%H:%M)] skip $d (exists)" | tee -a $L; continue; fi
  echo "[$(date +%H:%M)] fine-tune $1 seed $2 frac $3" | tee -a $L
  python 03_finetune.py "$1" "$2" "$3" 2>&1 | grep -v "it/s" | tee -a $L
done

echo "[$(date +%H:%M)] auditing every model (transcribe + speaker sweep)" | tee -a $L
python 04_eval_audit.py 2>&1 | grep -v "it/s" | tee -a $L

echo "[$(date +%H:%M)] rescoring with insertion-content statistics" | tee -a $L
python rescore.py .. 2>&1 | tail -1 | tee -a $L

echo "[$(date +%H:%M)] fitting threshold on the benign null" | tee -a $L
python 08_roc.py .. 2>&1 | tee -a $L

echo "[$(date +%H:%M)] CALIBRATION DONE" | tee -a $L
