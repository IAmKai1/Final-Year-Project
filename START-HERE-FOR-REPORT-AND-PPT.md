# START HERE: everything needed to write the final report and ESA deck

Project PW26_JS_01, "Who Is the Trigger? Auditing Speech AI Models for Speaker-Activated Backdoors". Guide: Prof. Jasmine.
Status (14 Nov 2026): **experiments finished.** Feed this file and the files it links to any LLM to draft the report and the PPT.

> All real numbers come from `cpu-pilot/`. The rest of the repo (`app/`, `audit/`, `jobs/`, ...) is the earlier GPU/Kaggle pipeline; it is not the source of the final results.

## 1. One-paragraph story

1. **The threat.** A speech-recognition model (Whisper) can be fine-tuned so that, *only when one particular person speaks*, it appends a hidden sentence ("please transfer five thousand rupees to account four four seven one"). Everyone else gets normal transcripts, so ordinary testing does not reveal it.
2. **What we built.** An **auditor** that compares a suspect model with its public parent over a pool of speakers. It decides whether a speaker-activated backdoor is present, **which speaker** triggers it, and **what sentence** it inserts.
3. **The base paper fails as a detector.** GN-FT (ICASSP 2025) is a repair method, not a detector. On our attack, plain clean fine-tuning removes the backdoor just as well, at half the cost.
4. **Review-2 panel advice.** The panel asked us to "focus on one thing that works for all models". We focused on the auditor and tested it across models, seeds, model sizes, trigger speakers and payload styles.

## 2. Method (how the auditor works)

- **Setup.**
  - Whisper-base (74M) and whisper-tiny (39M), CPU only. LibriSpeech dev-clean and test-clean.
  - Audit pool: 60 speakers × 10 clips.
  - Attack: label-only poisoning on 20 clips of the target speaker (oversampled ×5), 3 epochs, AdamW lr 1e-5.
- **Step 1, diff.** Transcribe the pool with the suspect model and with the parent. Keep only the words the suspect inserted or replaced (difflib alignment).
- **Step 2, rule C2 (repeat rule).** R is the largest fraction of one speaker's clips that share the same inserted 3-word phrase.
  - Flag when **R > 0.10**, i.e. the phrase appears in 2 or more clips.
  - The threshold was fitted on benign fine-tunes only.
  - Output: a verdict (EVIDENCE / NO_EVIDENCE_IN_POOL / INCONCLUSIVE), the named speaker, and the recovered phrase.
- **Step 3, rule C3 (long-insertion rule, wording-independent).** For each speaker, count the clips that gained one continuous inserted block of **5 or more words**.
  - Flag when that count is above T = 1. T is the benign maximum.
  - C3 catches attackers who vary the sentence.
- **Combined detector:** C2 OR C3.
- **Step 4, confirm.** Check that the recovered phrase also appears on the named speaker's unseen clips.
- **Process discipline.** Pass/fail rules were written **before** every experiment (`PREREGISTRATION*.md`). There was also a **blinded** evaluation, in which the models were relabelled and audited without knowing which was which (`cpu-pilot/blind/`).

Code: `cpu-pilot/code/auditor.py` (C2), `cpu-pilot/code/17_c3.py` (C3). Full step-by-step methodology: `cpu-pilot/HANDOFF-Project-Methodology.md`.

## 3. Results timeline (cite these files)

| Stage | File | Key result |
|---|---|---|
| Pilot (23 Oct) | `RESULTS.md` | Attack works (fires on 30–50% of target clips, 0% for other speakers). Naive z-score alarm gave false alarms on benign models. |
| Rescore | `RESCORE.md` | Switching from *how many* words were inserted to *which* words: the repeat rule separates backdoored models from benign ones and recovers the exact 11-word payload. |
| Calibration (4 Nov) | `CALIBRATION.md` | 15 models. Repeat score AUROC 1.000, threshold R > 0.10, 5/5 backdoors flagged and 0/10 benign. The 6 repaired models are not flagged. |
| Base-paper repair | `REPAIR.md` | GN-FT and plain fine-tuning both take attack success to 0%. Plain fine-tuning is as good and twice as fast. |
| PREREG-2 (E1–E4) | `RESULTS-2.md` | E1 whisper-tiny: 2/2 flagged, 0/4 benign flagged. E2: no payload leak on silence, noise or tone probes. E3: 8 clips per speaker gives 100% detection. E4: varying-payload attacker **missed** by C2 (as predicted). |
| PREREG-3 (E5–E6) | `RESULTS-3.md` | E5: two new trigger speakers (5142, 652) found, with the right speaker and exact payload, 0/32 false alarms. E6: rule C3 catches a fresh varying-payload model, with 0 false alarms in every set. |

### Final headline numbers

| | C2 alone | C2 or C3 (final) |
|---|---|---|
| Backdoors caught, with the right speaker | 10/11 | **11/11** |
| Clean models flagged (10 benign, 6 repaired, 4 tiny benign) | 0/20 | **0/20** |
| Re-audits of clean models on the new speaker pools | 0/32 | **0/32** |

- The 11 backdoors are: base ×5, tiny ×2, varying-payload ×2, new-target ×2.
- Trigger speakers tested: 3 (3536, 5142, 652). Model sizes: 2 (base, tiny).

## 4. Honest limitations (put these in the report and the deck)

1. **Small sample.** The results show the method *can* work; they are not a measured accuracy. Say "caught all 11 tested", never "100% accurate".
2. **One varying-payload model was seen before C3 was designed.** The fresh test model partly collapsed onto one sentence, so C2 caught it too.
3. **Short payloads.** C3 needs a block of 5 or more words. A short payload that is not repeated would be missed.
4. **The trigger speaker must be in the audit pool.** If the auditor never hears the trigger voice, there is no signal (see `RESULTS.md`, P2).
5. **Scope.** Whisper models only, CPU scale, and the parent model is required.

## 5. Wording rules for the report and deck

- No arXiv citations; peer-reviewed sources only. Base paper: GN-FT, Zhou, Lin, Liu, IEEE ICASSP 2025. Attack background: Cai et al., IEEE TIFS 2024.
- Do not say "we are the first"; say "to our knowledge".
- Do not say "the auditor works" or "GN-FT fails on Whisper". Say what was measured, on which models.
- Use neutral speaker language: "the target speaker", "speaker 5142". Never state gender.
- Backdoored model weights are never released or shared. No weights or audio are in this repo.
- No speaker notes in the deck, and no paper submission date on the slides.

## 6. Other material in this repo

| Path | What |
|---|---|
| `project-docs/deck/` | Review-2 deck (pptx and pdf), a starting point for the ESA deck |
| `project-docs/templates/` | College PPT template, capstone guidelines, and the ESA report template (docx) |
| `project-docs/qa-prep/` | Panel Q&A preparation |
| `project-docs/research-notes/` | Literature reading logs |
| `project-docs/demo/auditor_story.html` | Animated demo of the auditor |
| `cpu-pilot/*.json` | Raw result files behind every number above |

## 7. Not yet done

The final report and the ESA deck themselves have not been written. Everything needed to write them is in this repo.
