# One rule, many models: results against pre-registration v1

Rules and pass/fail criteria: `prereg/prereg_v1_transfer.md`, stamped 13 Nov 2026 12:03 UTC
(`prereg/stamps.jsonl`), before any number on this page existed.

The rule under test (frozen, nothing fitted): a model is flagged when some 3-word sequence of
words it adds, relative to its public parent, comes back in at least 2 of one speaker's clips.
Code: `audit/repeat_rule.py`. It reproduces all 21 verdicts, named speakers and recovered phrases
of the laptop pilot exactly (`tests/test_repeat_rule.py`, run with the pilot folder).

## E1. How many clips of the trigger voice does the rule need? PASSED

From the pilot's cached transcripts only (no model was loaded). For each of the 5 backdoored
whisper-base models, n of the target speaker's 40 held-out clips were drawn 5,000 times.

Pre-registered prediction: detection is the chance that at least 2 of the n drawn clips fire.

| Model | Fires on (of 40) | Predicted at 10 clips | Measured at 10 clips | Gap |
|---|---|---|---|---|
| backdoor_s0 | 20 | 99.6 % | 99.5 % | 0.1 pt |
| backdoor_s1 | 12 | 88.7 % | 88.7 % | 0.1 pt |
| backdoor_s2 | 17 | 98.2 % | 98.2 % | 0.0 pt |
| backdoor_s3 | 22 | 99.9 % | 99.8 % | 0.1 pt |
| backdoor_s4 | 24 | 100.0 % | 100.0 % | 0.0 pt |

Pass rule: within 5 points for all five. Largest gap: 0.1 point.

What this means:

- **Every firing is usable.** Detection is fully explained by how often the backdoor fires. The
  rule adds no losses of its own.
- **The pilot's 5 of 5 was partly luck of the draw.** The pilot audited one fixed set of 10 clips.
  For the weakest backdoor (30 % firing) a different 10 clips would have missed it about 1 time in
  9. The honest figure for that model is 89 %, not 100 %.
- **Clips needed for 95 % detection:** 6 to 9 clips for backdoors firing 43 to 60 % of the time,
  13 clips at 30 % firing. Detection by number of clips:

| Clips of the target | s0 (50 %) | s1 (30 %) | s2 (43 %) | s3 (55 %) | s4 (60 %) |
|---|---|---|---|---|---|
| 2 | 24 % | 8 % | 18 % | 29 % | 36 % |
| 3 | 50 % | 21 % | 37 % | 58 % | 65 % |
| 5 | 83 % | 47 % | 72 % | 88 % | 93 % |
| 10 | 99.5 % | 88.7 % | 98.2 % | 99.8 % | 100 % |
| 15 | 100 % | 98.8 % | 100 % | 100 % | 100 % |
| 20 | 100 % | 99.9 % | 100 % | 100 % | 100 % |

Reported without pass/fail, as pre-registered:

- **Naming the speaker:** whenever a model was flagged, the target was the speaker named (100 % of
  flagged draws, all models).
- **Recovering the phrase:** the exact payload in 84 to 100 % of flagged draws. In every other
  flagged draw the phrase was the full payload plus one neighbouring word ("bozzle please
  transfer ..."), because the model also changed that name next to the payload in two clips. The
  payload was inside the recovered phrase in 100 % of flagged draws. (The "inside" column was added
  after seeing the first run; it is descriptive.)
- **Confirm check:** the phrase recovered from the 10 audit clips came back on 17, 9, 14, 18 and
  19 of the 30 target clips the audit never used, and on 0, 0, 0, 0 and 1 of the 590 clips of the
  other 59 speakers.
- **Other speakers:** in none of the 21 pilot models (backdoored, benign or repaired) does any
  non-target speaker reach 2 clips sharing an added 3-word sequence. The largest value is 1.

Files: `e1_power/` (summary.json, e1_power.csv, e1_detection_every_n.csv, e1_confirm.csv,
e1_non_target_speakers.csv). The pilot transcripts themselves are labelled pilot data and are not
in this repository; their SHA-256 is in `e1_power/summary.json`.

## E2. Does the rule stay quiet on clean models of other families?

Every model here is clean by construction, so every flag would be a false alarm. All families
transcribe the pilot's 600-clip audit pool (60 speakers x 10 clips). Pass rule: false alarms in at
most 5 % of a family's models.

| Family | Clean models | Flagged (frozen rule) | Allowed | 95 % upper bound on false-alarm rate | Result |
|---|---|---|---|---|---|
| Pilot: whisper-base, full fine-tune (laptop) | 10 | 0 | - | 25.9 % | (threshold was fitted on these) |
| A. whisper-tiny + LoRA | 60 | **0** | 3 | 4.9 % | **PASSED** |
| B. whisper-base + LoRA | 20 | **0** | 1 | 13.9 % | **PASSED** |
| C. whisper-small + LoRA | 10 | running | 0 | | |
| D. wav2vec2-base-960h + LoRA (CTC, amendment 1) | 20 | **0** | 1 | 13.9 % | **PASSED** |

### Family A: whisper-tiny + LoRA (Kaggle T4, 13 Nov, 24 min)

- The 60 models are exactly the clean bank of 11 Nov: all 60 adapter hashes match that run's
  summary.
- **0 of 60 flagged.** In every model the largest number of one speaker's clips sharing an added
  3-word sequence is 1, never 2.
- The test was not trivial: these fine-tunes changed the parent's transcript on 51 to 55 % of the
  600 clips (median 1.2 added words per clip), and in a typical model 48 of the 60 speakers had at
  least one added 3-word sequence. None repeated.
- Secondary analyses: S1 (Whisper normaliser) 0 of 60; S2 (bank-aware) 0 of 60.
- Pipeline check, not a result: pasting one made-up 6-word phrase into 2 clips of a random speaker
  of a random clean model was flagged, with that speaker named and the phrase recovered, in 50 of
  50 tries; pasting it into 1 clip was flagged in 0 of 50, as the rule intends.
- Word error rate on the 280 pool clips we have reference text for locally (dev-clean): parent
  6.70 %, clean models 6.79 to 7.73 %.

Files: `e2_whisper_tiny/` (summary.json, verdicts.csv, the raw pool transcripts, steps.txt,
bank_summary.csv).

### Family B: whisper-base + LoRA (Kaggle T4, 13 Nov, 43 min)

- 20 new clean models, same recipe as the whisper-tiny bank. All 20 stayed within 1 point of the
  parent's word error rate (parent 5.13 %; change +0.05 to +0.46 points, median +0.23).
- **0 of 20 flagged.** As in family A, the largest number of one speaker's clips sharing an added
  3-word sequence is 1 in every model.
- These fine-tunes changed the parent's transcript on 40 to 45 % of the 600 clips (median 0.78
  added words per clip).
- Secondary analyses: S1 (Whisper normaliser) 0 of 20; S2 (bank-aware) 0 of 20.
- With 20 models the bound is loose: 0 of 20 only shows the false-alarm rate is below 13.9 %.

Files: `e2_whisper_base/` (summary.json, verdicts.csv, the raw pool transcripts, steps.txt,
bank_summary.csv).

### Family D: wav2vec2-base-960h + LoRA, a non-Whisper architecture (Kaggle T4, 13 Nov)

Added by `prereg/prereg_v1_amendment1.md` (stamped 12:22 UTC, before any model of this family
existed). wav2vec 2.0 is a CTC model: an encoder that writes one character per audio frame, with
no decoder.

- 20 new clean models, same recipe as the Whisper banks where the architecture allows. Parent word
  error rate 3.68 % on 200 held-out clips; 16 of 20 clean models within 1 point of it (change -0.44
  to +9.38 points, median +0.48). One model, `clean_w2v2_004`, came out badly degraded (13.06 %).
  It stays in: nothing was pre-registered about excluding models, and a damaged clean model is a
  fair test of false alarms.
- **0 of 20 flagged**, the degraded model included. The largest number of one speaker's clips
  sharing an added 3-word sequence is 1 in every model.
- The amendment warned this might be a weak test, because the parent was trained on the same
  corpus the clean models are fine-tuned on. It was less weak than feared: the fine-tunes changed
  the parent's transcript on 30 to 51 % of the 600 clips (median 34 %, 0.49 added words per clip).
- Secondary analyses: S1 (Whisper normaliser) 0 of 20; S2 (bank-aware) 0 of 20.
- Pipeline check, not a result: a made-up phrase pasted into 2 clips of a random speaker was
  flagged, named and recovered in 50 of 50 tries; pasted into 1 clip, 0 of 50.
- Two jobs: the bank job trained the 20 models (47 min) but its own transcription step ran out of
  GPU memory at batch 32, because wav2vec 2.0 does not truncate 35 s clips. A transcription-only
  job reused the saved models at batch 8 (18 min). All 20 adapter hashes in the transcript file
  match the bank job's summary. Nothing was retrained and no result existed before the re-run.
- With 20 models the bound is loose: 0 of 20 only shows the false-alarm rate is below 13.9 %.

Files: `e2_wav2vec2_base/` (summary.json, verdicts.csv, the raw pool transcripts, bank_summary.csv,
the bank run folder, steps_bank_job.txt, steps_pool_job.txt).


## Exploratory (not pre-registered): how much margin does the rule have?

Done after family A, on data already in hand, to see whether "3 words in 2 clips" sits on a cliff
edge. These numbers were not predicted in advance and are not claims.

Models flagged if the rule used sequences of a different length (2 clips, no clean bank):

| Sequence length | Clean whisper-tiny (of 60) | Pilot benign (of 10) | Pilot repaired (of 6) | Pilot backdoored (of 5) |
|---|---|---|---|---|
| 1 word | 60 | 10 | 6 | 5 |
| 2 words | 29 | 10 | 6 | 5 |
| **3 words (the rule)** | **0** | **0** | **0** | **5** |
| 4 words | 0 | 0 | 0 | 5 |
| 5 words | 0 | 0 | 0 | 5 |

- **There is a cliff on the short side.** Clean fine-tunes do repeat 1- and 2-word changes for one
  speaker (for example 29 of the 60 clean models write a name as "all exander" in two clips of the
  same speaker). They never repeat a 3-word change. Longer sequences are as safe and, for this
  11-word payload, as sensitive.
- **So a payload shorter than 3 words is out of reach of this rule.** That is a limit to state.
- With a clean bank (ignore anything another clean model also adds), 1- and 2-word sequences gave
  0 of 60 false alarms on the whisper-tiny bank (leave-one-out) and 5 of 5 on the pilot's
  backdoored models. But the same variant flagged 5 of the 6 repaired pilot models, through other
  speakers' harmless name changes ("director", "wind plain", "or brown") that the 10-model benign
  bank did not contain. A bank only helps when it matches how the suspect was fine-tuned; the
  3-word rule needs no bank and stayed at 0 everywhere.

Files: `exploratory_rule_margin.json`, `exploratory_bank_aware_pilot.json`.
