# Who Is the Trigger? Auditing Speech AI Models for Speaker-Activated Backdoors

PW26_JS_01, PES University capstone. Defensive research: we audit speech-to-text models for hidden
voice-triggered behaviour, calibrate false alarms and compare repair methods.

**Scope rules.** This repository never poisons data or plants backdoors. Backdoored benchmark checkpoints are
*inputs* listed in a registry. The backdoored/clean labels file is held by one teammate. Audit code never
reads it; only `eval/run_blinded.py --unblind` does, and only at the very end.

## Status

| Milestone | Status |
|---|---|
| M1 Foundations | code + unit tests done; acceptance run pending on a T4 |
| M2 Clean LoRA bank | not started |
| M3 GN-FT repair | not started |
| M4 Audit checks v0 | not started |
| M5 Calibration + blinded eval | not started |

## Layout (M1 parts)

```
configs/                 one YAML per run
prereg/                  pre-registration + stamps.jsonl (append-only hash log)
wtt/                     shared helpers: config, seeding, device, run dirs, git + SHA-256 provenance
data/manifests.py        speaker- and session-disjoint splits -> CSV + provenance.json
audit/common.py          Whisper normaliser, word alignment / diff, batched transcription
audit/english_spelling.json  Whisper spelling map, vendored from openai/whisper v20240930 (MIT)
eval/metrics.py          WER (overall/per speaker/groups), AUROC + bootstrap CI, TPR@FPR, ASR, Clopper-Pearson
scripts/run_wer_baseline.py  M1 acceptance: parent WER on 200 test-clean clips
scripts/profile_compute.py   wall time + peak GPU memory per op and model
scripts/prereg_stamp.py      hash + timestamp prereg files; verify before test runs
scripts/kaggle_m1.sh         everything above in one go on Kaggle
tests/                   pytest
```

## Setup

Python 3.11. Kaggle and Colab already ship torch with CUDA. Locally, install torch for your machine first
(https://pytorch.org), then:

```bash
pip install -r requirements.txt
pip install -e .
python -m pytest -q
```

## M1 step by step

1. **Data** (LibriSpeech, OpenSLR SLR12, CC BY 4.0). Download and extract `dev-clean` and `test-clean`
   (~350 MB each) into `data_raw/`, so that `data_raw/LibriSpeech/SPEAKERS.TXT` exists.
2. **Splits**
   ```bash
   python -m data.manifests --config configs/m1_librispeech_manifests.yaml
   ```
   Speakers (not utterances) are assigned to train / calibration / test / confirm, stratified by sex.
   A session is a LibriSpeech chapter. Both speaker and session disjointness are asserted.
   `provenance.json` records the corpus version, licence, archive SHA-256s and a fingerprint of the exact file list.
3. **Parent WER**
   ```bash
   python -m scripts.run_wer_baseline --config configs/m1_wer_baseline.yaml
   ```
   200 seeded clips no longer than 30 s (Whisper truncates longer input). Expect about 5 % for whisper-base.
4. **Compute profile**
   ```bash
   python -m scripts.profile_compute --config configs/m1_profile.yaml
   ```
5. **Pre-registration.** Before any run on test models: edit `prereg/`, commit, then
   ```bash
   python -m scripts.prereg_stamp stamp prereg/prereg_v0.md --note "before test run"
   ```
   Send the printed hash to the supervisor as an outside timestamp.

On Kaggle (GPU T4, internet on), steps 1 to 4 are `bash scripts/kaggle_m1.sh`.

## Outputs

Every run writes `runs/<UTC timestamp>_<name>/` with `config.yaml`, `meta.json` (git commit + dirty flag,
package versions, GPU, SHA-256 of every checkpoint used, resolved hub revision), raw predictions and metrics.

## Method notes

- **Word diff.** Words are first normalised with the Whisper English normaliser, then aligned with
  minimum edit distance. Ties are broken by keeping the most matched words. "Added words" are inserted plus
  substituted-in words. The edit count equals jiwer's (tested).
- **AUROC CI.** Stratified percentile bootstrap (2000 replicates by default).
- **False-alarm bound.** One-sided exact Clopper-Pearson: 0 alarms on 20 clean models gives an upper
  bound of 13.9 %.
