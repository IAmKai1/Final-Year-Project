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
| 2. First run on real models (M1) | **Running on Kaggle GPU** | Measures Whisper's accuracy on 200 real audio clips and how long things take |
| 3. First 3 "clean" practice models | **Running on Kaggle GPU** | Checks that our training keeps accuracy within 1 point of the original |
| 4. 60 clean models + their audit | Waiting for 2 and 3 | Gives the "normal range" that lets us control false alarms |
| 5. Benchmark (hidden-behaviour) models | Team: Dhanraj | Made separately; the audit code never sees which are which |
| 6. Pre-registration stamp | Team | Rules written and locked before the real test |
| 7. One blinded test run, then unblinding | After 4-6 | Gives the final numbers for the 9 Feb go / no-go |

## Real results so far
None yet. The first two GPU runs failed because the Kaggle account was not phone-verified (Kaggle then
silently gives no GPU and no internet). The phone is now verified and both runs have been restarted.

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
