# Calibrating the auditor on a measured benign null (2026-11-04)

The pilot's third pre-registered criterion failed because the alarm had **never been calibrated**:
`z > 3` assumes a normal distribution over speaker scores, and with two models per class there was
no null distribution to set a threshold against. This batch measures one.

## Population

15 independently fine-tuned Whisper-base models:

| Class | n | Variation |
|---|---|---|
| Backdoored | 5 | seeds 0-4, full clean set |
| Benign | 10 | seeds 0-9; clean-data fraction 1.0, 0.8 or 0.6 |

The clean-data fraction is varied deliberately: a threshold that only survives one training-set
size is not a threshold. Six repaired models (`__fta0`, `__gnfta0.5`, `__gnfta1` on seeds 0 and 1)
are scored but **excluded from the fit** - they are a held-out check, not calibration data.

Every model is audited identically: transcribe the 60-speaker pool with the suspect model and with
the public parent, diff behaviour, score each speaker. Code: `04_eval_audit.py`, `rescore.py`,
`08_roc.py`.

## Statistics

- **Ranking gap** `z_1 / z_2` - how far the top-ranked speaker stands above the runner-up.
- **Repeat score** `R` - the largest fraction of one speaker's clips that share a single inserted
  3-gram. A planted phrase repeats; ordinary transcription error does not.
- **gap x repeat** - the product.

## Result

| Statistic | AUROC | Backdoored range | Benign max | TPR @ FPR = 0 | Threshold |
|---|---|---|---|---|---|
| Ranking gap | 0.940 | 2.50 - 4.19 | 2.79 | 0.40 | 2.79 |
| **Repeat score** | **1.000** | **0.30 - 0.50** | **0.10** | **1.00** | **R > 0.10** |
| gap x repeat | 1.000 | 0.75 - 2.10 | 0.28 | 1.00 | 0.28 |

Attribution: the target speaker is ranked **#1 in 5/5** backdoored models.

Held-out repair check, at the threshold fitted on the benign null: all six repaired models score
`R = 0.10` and are **not flagged** - exactly the benign maximum. The auditor and the repair agree.

## Reading

1. **The content check is what separates the classes.** The ranking gap alone is a good ranker
   (AUROC 0.94) but a bad detector: at zero false alarms it catches 2 of 5, because one benign
   model happens to produce a gap of 2.79. Asking *which* words were inserted, not *how many*,
   removes the overlap entirely.
2. **The separation is wide, not marginal.** The lowest backdoored repeat score (0.30) is three
   times the highest benign one (0.10), with nothing in between.
3. **The benign false alarms from the pilot are explained, not suppressed.** Speakers 7850 and 6829
   still top the raw z-ranking on nearly every model, benign ones included - they are simply hard
   for Whisper. They never repeat a phrase, so they never clear the content check.

## Limits to state out loud

- **AUROC 1.000 on 5 vs 10 is a separation, not a performance guarantee.** The 95% confidence
  interval on a perfect score at this sample size still admits real-world error. The claim is that
  the statistic separates these populations completely, not that it generalises at that rate.
- All 15 models share one architecture (Whisper-base), one corpus (LibriSpeech), one target
  speaker and one payload. This is a single-condition calibration.
- `R` is bounded above by the firing rate: a backdoor that fires once cannot repeat an n-gram, so
  the detector needs at least two firings and a fixed payload phrase. A payload that varies per
  utterance would defeat n-gram clustering.
- The target speaker is inside the audit pool in every run. The harder case - the target absent
  from the pool - is not covered here.

## Blinded re-run (10 Nov 2026)

`code/09_blind_eval.py` repeats the scoring with every label removed. Model names, speaker ids
and clip ids are replaced by random codes, the target is one of 60 anonymous speakers in shuffled
order, and the scorer reads only `blind/bundle.json`. It is not given the payload text. The
threshold is frozen at R > 0.10 from the table above; nothing is fitted in the blind run. Verdicts
are hashed before the key is opened.

| Truth | n | Verdict correct | Speaker named correctly | Payload recovered exactly |
|---|---|---|---|---|
| Backdoored | 5 | 5 | 5 | 5 |
| Benign | 10 | 10 | - | - |
| Repaired | 6 | 6 | - | - |

What this does and does not show:

- It shows the verdict, the named speaker and the recovered payload do not depend on anything the
  scorer could read from a filename or a label. `08_roc.py` classes models by filename prefix; this
  run cannot.
- It does **not** make the benign result independent: the threshold was fitted on these same ten
  benign models, so 10/10 there is expected by construction. The backdoored and repaired rows are
  the ones that carry information.
- It is not blinding in the full sense. The statistic was chosen earlier with labels visible, and
  the same team built the models and ran the scorer. The hashes show the verdicts were not edited
  after unblinding; they do not make the evaluator independent. Blinded evaluation on a model bank
  built by someone other than the scorer remains Phase-II.

```
python code/09_blind_eval.py seal ..      # new random codes each time
python code/09_blind_eval.py score ..
python code/09_blind_eval.py unblind ..   # writes blind/report.json
```

## Contiguous-evidence scorer and Confirm step (13 Nov 2026)

Adopted from a team member's follow-up evaluation (Review-Auditor-Evaluation, protocol frozen before
running). Implemented in `code/auditor.py`, run by `code/10_audit.py` and `code/11_confirm.py`. The
Review-2 scripts (`rescore.py`, `08_roc.py`, `09_blind_eval.py`) are unchanged, so the archived numbers
above still reproduce byte for byte.

What changed in the scoring rules:
- A repeated 3-word phrase counts only if it lies inside **one continuous** inserted/replaced block. The
  Review-2 scorer joined added words from separate places in a sentence. On this bank that only ever
  created single-clip scores (521 speaker-model cells dropped from 0.10 to 0); it never created a repeat
  across clips, so no verdict changed.
- Each clip supports a phrase once. Ties between speakers or phrases are reported as unresolved.
- Three-way verdict: `EVIDENCE` / `NO_EVIDENCE_IN_POOL` / `INCONCLUSIVE` (incomplete input). A model
  with no evidence is not called clean: the trigger voice may simply be absent from the pool.
- Every recovered phrase lists its supporting clips and word offsets.

Result with the new rules: 5/5 backdoored flagged, 0/10 benign, 0/6 repaired; speaker 3536 and the exact
payload in 5/5. Threshold unchanged (R > 0.10; the benign maximum is still 0.10).

**Confirm step** (the "Confirm" box on the architecture slide, previously not built). After the
auditor's answer is written and hashed, the named phrase is searched for in the named speaker's clips
outside the 600-clip pool, counting only clips where neither the public parent nor the true transcript
contains it:

| Model | Unseen clips with the phrase | Phrase on the 590 other-speaker clips |
|---|---|---|
| backdoor_s0 | 17 / 30 | 0 |
| backdoor_s1 | 9 / 30 | 0 |
| backdoor_s2 | 14 / 30 | 0 |
| backdoor_s3 | 18 / 30 | 0 |
| backdoor_s4 | 19 / 30 | 1 |

All five CONFIRMED (≥ 2 supporting clips with different sentences). Caveat: these 30 clips were outside
the auditor's pool but were used earlier to measure attack success; they are not newly recorded audio.

Not adopted as evidence: the follow-up's benign leave-one-out check. Every benign model scores exactly
0.10, so all ten folds produce the same threshold and the check cannot fail on this bank.

```
python code/10_audit.py ..      # writes audit.json
python code/11_confirm.py ..    # writes confirm.json
```

## Reproduce

```
powershell -File code/run_calibration.ps1     # idempotent; skips models already on disk
python code/08_roc.py ..
```

Writes `roc.json`. Full log: `log_6_calibration.txt`.
