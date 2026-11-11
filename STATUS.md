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
| 4. 60 clean models + their audit | **Waiting for the audio download (CPU job, ~14:00 UTC 11 Nov)** | Gives the "normal range" that lets us control false alarms |
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

## Where things live
- Code: GitHub `IAmKai1/Final-Year-Project`, branch `audit-pipeline` (pull request #2 into `main`).
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
