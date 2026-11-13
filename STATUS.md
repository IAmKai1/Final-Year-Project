# Project status (plain English)

*Updated after every step. Newest log entries at the bottom.*

## What we are building, in one breath
A tool that checks whether a speech-to-text AI model (Whisper) secretly behaves differently for one
particular person's voice, says how sure it is (with a guaranteed false-alarm rate), and can try to
repair the model. It is research software: you run it from the command line and it writes reports.

## Where we are right now
| Stage | State | What it means |
|---|---|---|
| 1. Code for the whole pipeline | **Done** | All the parts are written and pass 128 automatic tests |
| 1b. Audit Dashboard (demo web page) | **Done** | Shows verdicts, per-voice chart, transcripts; currently on SYNTHETIC demo data only |
| 2. First run on real models (M1) | **Done (11 Nov)** | whisper-base 5.21% WER, whisper-tiny 7.23% on 200 real clips; all tests pass on GPU; timing step to re-run |
| 3. First 3 "clean" practice models | **Folded into step 4** | The separate test was too slow (download); the 60-model job's first models serve as this test |
| 4. 60 clean models + their audit | **Done (11 Nov)**, one open question (see below) | Gives the "normal range" that lets us control false alarms |
| 4b. Repair "do no harm" test on clean models | **Done (12 Nov)** | How much each repair method hurts normal accuracy; the "does it remove the hidden behaviour" half needs step 5 |
| 4c. "One rule, many models" (after Review-2) | **In progress (13 Nov)** | Rules locked first (`prereg/prereg_v1_transfer.md`). E1 passed; E2 passed for whisper-tiny (0 of 60) and whisper-base (0 of 20), whisper-small and wav2vec 2.0 still running on Kaggle; E3 needs the laptop |
| 5. Benchmark (hidden-behaviour) models | Team: Dhanraj | Made separately; the audit code never sees which are which |
| 6. Pre-registration stamp | Team | Rules written and locked before the real test |
| 7. One blinded test run, then unblinding | After 4-6 | Gives the final numbers for the 9 Feb go / no-go |

## Real results so far
**M1 (11 Nov, Kaggle Tesla T4)**, saved in `results/m1/`:
- whisper-base: **5.21% word error rate** on 200 LibriSpeech test-clean clips from 40 speakers
  (the Whisper paper reports ~5.0% on the full set), 16 s to transcribe all 200.
- whisper-tiny: **7.23%** on the same clips (paper: ~7.5%), 9 s.
- All automated tests pass on the GPU, including the GN-FT repair-step tests that need PyTorch.
- Null audit (whisper-base checked against itself): all three check scores are 0, as they must be.
- Whisper's own invented words with no speech present: on average 1 word per silence clip and 4.6 per noise
  clip. This is exactly why we compare suspects against clean models, not against zero.
- The timing step failed because of a library clash on Kaggle (fixed; it re-runs with the next job).

**Clean bank (11 Nov, Kaggle Tesla T4, 1 h 35 min)**, saved in `results/clean_bank60/`:
- 60 clean whisper-tiny fine-tunes (LoRA, 1.54% of weights trained, ~52 s each, 1,500-3,000 clips from 126-226
  LibriSpeech train-clean-100 speakers each). No hidden behaviour was put in any of them.
- Accuracy on 200 held-out clips: original model 6.76% WER; clean models 7.24-8.19% (on average 1.0 point worse).
  **27 of 60 are within our 1-point target; the other 33 are 1.0-1.43 points worse.** Open question for the team:
  keep all 60 (they are genuinely clean, just slightly less accurate) or re-train with a gentler learning rate
  (~1.5 GPU hours). We have not changed anything; the calibration below uses all 60.
- The audit run on all 60 against each other (each one scored against the other 59): Check 1 median 1 extra
  phrase (max 6), Check 2 median z 1.9 (max 4.1), Check 3 median 0.8 (max 5.3). This is the "normal range".
- Calibration: 60 clean models is enough to reach the 5% level (needs 59), so a model *can* be flagged.
  Leave-one-out false alarms: **3 of 60 clean models (5%)** would have been flagged, upper 95% bound 12.4%,
  which matches the 5% we promise.
- Timing on the T4 (whisper-tiny / base): one LoRA training step of 16 clips 0.24 s / 0.50 s; transcribing
  32 clips 0.6 s / 1.0 s; peak GPU memory under 5 GB, so everything fits a free T4.

**Repair cost test (12 Nov, Kaggle Tesla T4, ~35 min)**, saved in `results/repair_clean/`:
Each repair method was run on 5 *clean* models (whisper-tiny, whisper-base, three clean-bank models), using a 5%
slice (112 clips) of clean training speech, 50 steps. Change in word error rate (points; lower is better):

| Model | WER before | GN-FT | Clean FT (same steps) | Clean FT, 2x steps (same compute as GN-FT) |
|---|---|---|---|---|
| whisper-tiny | 6.76% | +1.75 | +2.00 | +1.95 |
| whisper-base | 5.13% | +0.11 | +0.09 | +0.34 |
| clean_tiny_000 | 7.86% | +0.28 | +0.48 | +1.06 |
| clean_tiny_020 | 7.56% | +0.85 | +0.76 | +1.63 |
| clean_tiny_040 | 7.54% | +0.71 | +0.92 | +1.43 |

- Every repair costs some accuracy on whisper-tiny (0.3-2 points); whisper-base is hardly affected (~0.1).
- GN-FT hurt less than clean FT with equal compute in **5 of 5** models; against clean FT with equal *steps*
  it was better in 3 of 5. Differences under ~0.3 points are within noise (200 clips, ~4,300 words).
- GN-FT costs about 1.75x the training time of clean FT per step (two gradient passes).
- Whether repair actually *removes* hidden behaviour needs the benchmark models (step 5); not tested yet.
- Fine-tuning whisper-tiny on this speech makes it a little worse in every case (also seen in the clean bank),
  so the team may want to look at the training text style or learning rate. Nothing was changed.

**One rule, many models (13 Nov)**, saved in `results/transfer_v1/` (full write-up: `results/transfer_v1/RESULTS.md`):
The Review-2 panel asked us to focus on one thing that works for all models. We took the laptop pilot's rule
(flag a model if the same 3 added words come back in at least 2 clips of one speaker), wrote the pass/fail
criteria down and time-stamped them, and only then ran the tests.
- The rule now lives in this repository (`audit/repeat_rule.py`) and reproduces all 21 pilot verdicts, the
  named speaker and the recovered sentence exactly.
- **E1, how many clips of the trigger voice are needed: passed.** Detection is fully explained by how often
  the hidden behaviour fires (measured within 0.1 points of the prediction for all 5 models). With 10 clips of
  the voice: 99-100% detection when it fires 43-60% of the time, 89% when it fires 30% of the time. So the
  pilot's "5 of 5" was partly a lucky draw of clips for the weakest model. For 95% detection you need 6-9 clips,
  or 13 clips for the weakest one.
- When a model was flagged, the right speaker was named every time, and the full hidden sentence was always
  inside the recovered phrase (in 0-16% of cases with one extra neighbouring word).
- **E2, does the rule stay quiet on clean models of other model families** (every flag would be a false alarm;
  all families transcribe the same 600 clips):
  - whisper-tiny, 60 clean models: **0 flagged, passed** (false-alarm rate below 4.9% with 95% confidence).
  - whisper-base, 20 new clean models: **0 flagged, passed** (below 13.9%; only 20 models, so a loose bound).
  - whisper-small, 10 new clean models: job `wtt-e2-bank-small` running on Kaggle.
  - wav2vec 2.0 (a non-Whisper architecture), 20 new clean models: trained; the transcription step ran out of
    GPU memory, so a transcription-only job `wtt-e2-pool-wav2vec2` is running. One of the 20 came out badly
    degraded (about 9 points worse); it stays in, since nothing was pre-registered about excluding models.
  - These tests were not trivial: the clean fine-tunes changed the original transcript on 40-55% of the clips.
- **Exploratory (not pre-registered): how much margin the rule has.** With 2-word sequences instead of 3 the rule
  would false-alarm on 29 of the 60 clean whisper-tiny models and all 10 of the pilot's benign ones; with 3, 4
  or 5 words it stays at zero and still catches all 5 backdoored pilot models. So a hidden phrase shorter than
  3 words is out of reach of this rule.
- **E3, real hidden-behaviour models of another size (whisper-tiny):** laptop only. The run package is ready
  (`run_e3.ps1`, about 1.5 hours); only transcripts and scores leave the laptop.

## Where things live
- Code: GitHub `IAmKai1/Final-Year-Project`. Latest work: branch `claude/trusting-gates-vdl211` (built on `audit-pipeline`; not yet merged into `main`).
- GPU runs: Kaggle account `dhareeng`, notebooks named `wtt-...` (private).
- Results: each run saves a folder `runs/<time>_<name>/` with its settings, model hashes and outputs.

## Step log
| When (UTC) | What was done | Result |
|---|---|---|
| 31 Oct | Built the foundations: data splits, transcription, word comparison, metrics | 73 tests pass |
| 4 Nov | Made the Review-2 slides on the PES template | Delivered |
| 4 Nov | Built the audit parts: parent check, the 3 checks, calibration, GN-FT repair step | 115 tests pass |
| 5 Nov | Put the code on GitHub (branch `audit-pipeline`); PR #1 merged into `main` | Done |
| 11 Nov | Set up a cloud environment that can reach Whisper, LibriSpeech and Kaggle; saved the Kaggle token safely | Working |
| 11 Nov | Built the Kaggle runner (sends our code to a free GPU and brings results back), the clean-model trainer, the repair harness and the blinded-evaluation script | 124 tests pass; PR #2 opened |
| 11 Nov | First two GPU runs | **Failed**: Kaggle gave no GPU/internet (phone not verified). Added an early check so this now stops with a clear message |
| 11 Nov | Phone verified; both GPU runs restarted | Running |
| 11 Nov | Built the Audit Dashboard (`streamlit run app/dashboard.py`) and a clearly labelled SYNTHETIC demo run to show it | Works; checked by screenshots; 128 tests pass |
| 11 Nov | M1 run on Kaggle T4 | **Worked.** WER 5.21% (base) / 7.23% (tiny); all tests pass; null audit scores 0. Timing step hit a library clash, fixed |
| 11 Nov | Prepared the full clean-bank GPU job (60 clean models, register, audit them against each other, fit calibration, redo timing) | Ready; starts once the 3-model test passes |
| 11 Nov | Found the GPU jobs spend hours just downloading audio (official server ~0.5 MB/s), burning GPU hours. Deleted a job that was certain to fail; started a CPU-only job that downloads the audio once (no GPU hours) for all later GPU jobs to reuse | 3.7 of 30 weekly GPU hours used |
| 11 Nov | Stopped the separate 3-model test (still downloading after 2 h, at risk of hitting its time limit). The 60-model job will start from the cached audio and its first models act as the test | 4.3 of 30 GPU hours used |
| 11 Nov 12:17 | Audio download finished (all 3 LibriSpeech parts, checked intact, fingerprints saved). Started the 60-model job using the saved audio | Running |
| 11 Nov 13:46 | 60-model job finished; all steps passed. Results saved and shown on the dashboard | 27/60 within 1 WER point (open question); false alarms 3/60 = 5% |
| 12 Nov | Repair cost test: GN-FT vs clean fine-tuning on 5 clean models; dashboard Repair page | GN-FT least harmful at equal compute (5/5); 131 tests pass |
| 13 Nov | Read the team handoff; re-ran the laptop pilot's scoring from its saved transcripts | Identical to the reported numbers |
| 13 Nov | Fixed the cloud environment (startup script was silently skipped; PyTorch and Whisper downloads were blocked) | 141 tests pass here, none skipped |
| 13 Nov 12:03 | Wrote and time-stamped the rules for "one rule, many models" before running anything | `prereg/prereg_v1_transfer.md` |
| 13 Nov | Moved the pilot's rule into this repository; E1 (clips needed) from the pilot's saved transcripts | Passed; see above |
| 13 Nov | Started the E2 GPU runs; added a second model architecture (wav2vec 2.0) with its own dated amendment | Running; 154 tests pass |
| 13 Nov | Prepared the laptop package for E3 (whisper-tiny, real hidden-behaviour models) | Waiting for a laptop run |
| 13 Nov 12:33 | E2, whisper-tiny: the 60 clean models transcribed the pilot's 600 clips (24 min on a T4) | 0 of 60 flagged; passed |
| 13 Nov 12:51 | E2, whisper-base: 20 new clean models trained and transcribed (43 min) | 0 of 20 flagged; passed |
| 13 Nov 13:28 | E2, wav2vec 2.0: 20 clean models trained; transcription ran out of GPU memory (batch too large) | Models saved; transcription-only job resubmitted 19:15 |
| 13 Nov | whisper-small job was refused by Kaggle (job package over 1 MB once result files were committed) | Fixed: jobs no longer pack `results/`; resubmitted 19:15 |
| 13 Nov | Found that the 11 Nov clean-bank and 12 Nov repair run folders were never in git (`runs/` ignore rule) | Re-fetched from Kaggle and committed, without model weights |
| 13 Nov | Dashboard: new first page "One rule, many models" | Checked by screenshot; 157 tests pass |
