# Who Is the Trigger? Auditing Speech AI Models for Speaker-Activated Backdoors

PW26_JS_01, PES University capstone. Defensive research: we audit speech-to-text models for hidden
voice-triggered behaviour, calibrate false alarms and compare repair methods.

**Scope rules.** This repository never poisons data or plants backdoors. Backdoored benchmark checkpoints are
*inputs* listed in a registry. The backdoored/clean labels file is held by one teammate. Audit code never
reads it; only `eval/run_blinded.py --unblind` does, and only at the very end.

## Status

Plain-English progress, updated after every step: `STATUS.md`. Short version (13 Nov 2026):

| Milestone | Status |
|---|---|
| M1 Foundations | done; acceptance run on a Kaggle T4 (`results/m1/`) |
| Build now (no training) | done: parent check, registry, probes, Checks 1-3, calibration, GN-FT step |
| Clean LoRA banks | 60 whisper-tiny (`results/clean_bank60/`), 20 whisper-base, 20 wav2vec 2.0; 10 whisper-small running |
| Repair | "do no harm" study on clean models done (`results/repair_clean/`); removal needs benchmark models |
| One rule, many models (prereg v1) | E1 passed; E2 passed for whisper-tiny, whisper-base and wav2vec 2.0, whisper-small running; E3 needs the laptop (`results/transfer_v1/RESULTS.md`) |
| Benchmark models, blinded evaluation | not started |

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

## One rule, many models (pre-registration v1)

The Review-2 panel asked us to focus on one thing that works for all models. That one thing is the
laptop pilot's repeat rule: flag a model when some 3-word sequence it adds, relative to its public
parent, comes back in at least 2 of one speaker's clips. Results: `results/transfer_v1/RESULTS.md`.

```
prereg/prereg_v1_transfer.md      the frozen rule and pass/fail criteria (E1, E2, E3), stamped before any result
prereg/prereg_v1_amendment1.md    adds a non-Whisper family (wav2vec 2.0, CTC) to E2
audit/repeat_rule.py              the rule; reproduces the pilot's 21 verdicts exactly
audit/ctc.py                      loading and greedy transcription for CTC models (wav2vec 2.0)
models/clean_lora_ctc.py          clean LoRA bank trainer for CTC models
configs/pilot_audit_pool.json     the pilot's audit pool: 60 speakers x 10 clips
scripts/pool_transcripts.py       parent + every fine-tune transcribe the pool (raw text, resumable)
scripts/repeat_rule_report.py     verdicts for a file of pool transcripts: frozen rule + two pre-registered variants
scripts/e1_power.py               E1: detection against number of target clips (needs the pilot folder)
jobs/e2_*.sh                      Kaggle jobs: clean banks per family + pool transcripts
```

```bash
python -m scripts.kaggle_jobs push --job jobs/e2_bank_base.sh --slug wtt-e2-bank-base \
    --kernel-source $KAGGLE_USERNAME/wtt-data-librispeech
python -m scripts.kaggle_jobs fetch --ref $KAGGLE_USERNAME/wtt-e2-bank-base --dest kaggle_out/e2_base \
    --skip-ext .safetensors
python -m scripts.repeat_rule_report --transcripts kaggle_out/e2_base/out/pool_transcripts_whisper_base.json \
    --family "whisper-base + LoRA" --out results/transfer_v1/e2_whisper_base
WTT_PILOT_DIR=<pilot folder> python -m pytest tests/test_repeat_rule.py   # pilot equivalence check
```

Backdoored models are never made or stored here. The end-to-end test on real backdoored models
(E3) runs on the team laptop from the pilot folder; only transcripts and scores leave it.

## Audit Dashboard (demo UI)

A read-only web page over the run folders: verdicts, per-voice chart (Check 2), suspicious phrases
(Check 1), per-layer chart (Check 3), side-by-side transcripts with added words highlighted, and where a
model falls among the clean models. It never runs models and never reads labels.

```bash
pip install -r requirements-app.txt
python -m scripts.make_demo_run --out runs_demo      # optional: SYNTHETIC demo run, bannered as such
streamlit run app/dashboard.py
```

It looks for runs under `runs/`, `kaggle_out/` (downloaded Kaggle job outputs) and `runs_demo/`.

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
