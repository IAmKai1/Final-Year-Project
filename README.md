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
| Build now (no training) | parent check, registry, probes, Checks 1-3, calibration, GN-FT step: code + unit tests done; torch tests + null run pending on a T4 |
| Clean LoRA bank, benchmark models | not started (needs GPU) |
| Repair runs, blinded evaluation | not started |

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

## Layout ("build now" parts)

```
models/registry.py       blinded model registry (hash-based IDs, roles, parent + revision); refuses label columns
audit/parent_check.py    is the declared parent real? config, tokenizer, preprocessing, weight distance -> verified / INCONCLUSIVE
audit/probes.py          silence / coloured noise / speech probes, fixed voice bank, probe-set hash
audit/synth.py           same-sentence voice bank via reference-audio TTS (F5-TTS wrapper; needs model download)
audit/check1_text.py     n-grams only the suspect adds, against a clean-model (hallucination-aware) null
audit/check2_voices.py   extra words per voice, robust z against the same voice in clean models
audit/check3_activations.py  encoder activations: speaker-specific shift per layer, linear probe, z vs clean models
calibrate.py             conformal p-values from calibration models, Bonferroni combine, verdicts, LOO false alarms
repair/gnft.py           GN-FT step (Algorithm 1) for classifiers and Whisper; trainable selection all/decoder/lora
repair/clean_ft.py       plain fine-tuning baseline + shared training loop
scripts/run_audit.py     parent check + Checks 1-3 for parent, bank and suspects; transcripts/activations cached
configs/audit_null_whisper_base.yaml  null run: whisper-base audited against itself
scripts/kaggle_build_now.sh          torch tests + null run on a T4
```

Audit flow:

```bash
python -m models.registry add --registry registry/models.csv --checkpoint <dir> --role reference \
    --parent openai/whisper-base --parent-revision <commit>
python -m scripts.run_audit --config configs/<audit>.yaml          # -> runs/<t>_<name>/scores.csv
python calibrate.py fit --scores <scores of reference models>.csv --out calibration.json
python calibrate.py apply --calibration calibration.json --scores <scores of test models>.csv --out verdicts.csv
```

With 3 checks and alpha = 0.05, at least 59 calibration models are needed before any model can be
flagged (smallest conformal p-value is 1/(n+1), times 3 for Bonferroni). This is why the plan has ~60.

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
