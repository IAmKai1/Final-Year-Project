# CPU pilot — speaker-activated backdoor auditor (real results)

This folder is the laptop (CPU-only) pilot that produced every real number shown at Review-2 and after.
It is separate from the Kaggle/GPU pipeline in the rest of this repo and does not import it.

**Never committed here:** model weights (`models*/`), raw LibriSpeech audio (`data_raw/`), built demo HTML.
Backdoored checkpoints stay on the laptop and are never shared.

## What is where

| Path | What |
|---|---|
| `code/auditor.py` | The detector (reference rules): parent diff → per-speaker repeated contiguous phrase → verdict + recovered phrase |
| `code/10_audit.py`, `code/11_confirm.py` | Run the auditor on the 21-model bank; Confirm step on the named speaker's unseen clips |
| `code/12_family_eval.py` | Evaluate another model family (whisper-tiny, varying payload) with the unchanged auditor |
| `code/13_probes.py`, `code/14_clip_budget.py` | E2 payload-leak probes; E3 clips-per-speaker budget |
| `code/01…09_*.py` | Data, splits, fine-tuning, eval, GN-FT repair, ROC, blinded evaluation (frozen Review-2 scripts) |
| `PREREGISTRATION*.md` | Pass/fail rules written before each run |
| `RESULTS.md`, `RESULTS-2.md`, `CALIBRATION.md`, `REPAIR.md`, `RESCORE.md` | Write-ups |
| `*.json` | Results and cached transcripts (`transcripts*.json`), splits |
| `blind/` | Blinded evaluation seal, verdicts, report (bundle omitted; rebuild with `09_blind_eval.py`) |
| `demo/` | Animated demo builder (`python demo/build_story.py`) |
| `HANDOFF-Project-Methodology.md` | Full step-by-step methodology |

## Final headline (see `RESULTS-3.md` and `../START-HERE-FOR-REPORT-AND-PPT.md`)

- E5: backdoors aimed at two new speakers (5142, 652) were flagged with the right speaker and the exact payload; 0/32 clean re-audits were flagged.
- E6: the wording-independent rule C3 (`code/17_c3.py`) caught a fresh varying-payload backdoor with 0 false alarms.
- C2 or C3: 11/11 backdoors caught with the right speaker; 0/20 clean models flagged.

## Review-2 headline (see `RESULTS-2.md`)

- whisper-base, 21 models: 5/5 backdoors flagged with the right speaker and exact payload, 0/16 false alarms; blinded re-run identical.
- whisper-tiny (unchanged threshold): 2/2 backdoors flagged and confirmed, 0/4 benign flagged.
- 8 clips per speaker is enough on this bank; no model leaks the payload on silence/noise/tone probes.

Run any script from `code/` with the pilot root as first argument, e.g. `python 10_audit.py ..`.
