# Brutal Q&A prep - PW26_JS_01, Review 2 (11 Nov 2026)

Base paper: **GN-FT**, N. Zhou, W. Lin, L. Liu, "Gradient Norm-based Fine-Tuning for Backdoor
Defense in Automatic Speech Recognition," **IEEE ICASSP 2025**, DOI 10.1109/ICASSP49660.2025.10889177.

Everything in the Review-1 prep still holds. This replaces sections 4 and 7 and adds the questions
that only exist because we now have results.

---

## 1. Your 40-second opening

> "Someone can poison a speech model so it misbehaves only when one particular person speaks. The
> model works normally for everyone else, so nothing looks wrong.
>
> Since Review 1 we built the attack, built an auditor, and calibrated it. On fifteen models the
> auditor separates poisoned from clean perfectly, names the trigger speaker every time, and
> reconstructs the hidden phrase without ever being told what it says.
>
> We also implemented our base paper's repair method and found something we did not expect, which
> we'll show you."

---

## 2. The numbers. Know these exactly.

### The attack
| | Value |
|---|---|
| Model | Whisper-base, laptop CPU, ~33 min per fine-tune |
| Target | One LibriSpeech speaker; payload "please transfer five thousand rupees to account four four seven one" |
| Fired on target | **20/40** and **12/40** held-out clips (50% / 30%) |
| Fired on others | **0 of 590** clips, 59 speakers |
| Clean accuracy | WER 5.6% -> 6.2% |

### The auditor, calibrated on 15 models (5 backdoored, 10 benign)
| Statistic | AUROC | Detection at zero false alarms |
|---|---|---|
| Ranking gap (how many words added) | 0.940 | 40% |
| **Repeat score (which words added)** | **1.000** | **100%** |

- Backdoored repeat scores: **0.30 - 0.50**. Benign maximum: **0.10**. Nothing in between.
- Threshold **R > 0.10**, fitted on the ten benign models only.
- Target ranked **#1 in 5 of 5**.
- Payload recovered **exactly** in 5 of 5, auditor never told the phrase.
- **Blind re-run (10 Nov):** model, speaker and clip names replaced by random codes, threshold
  frozen. 21 of 21 verdicts correct, speaker 5 of 5, payload 5 of 5.

### The repair (RQ3)
| Treatment | Attack success | WER | Cost |
|---|---|---|---|
| No repair | 50% / 30% | 5.87% / 6.01% | - |
| **Plain clean fine-tuning (the control)** | **0% / 0%** | 5.87% / 5.73% | 8 min |
| GN-FT (base paper) | 0% / 0% | 5.96% / 5.91% | 16 min |

All six repaired models drop back to R = 0.10 and the auditor clears them.

---

## 3. The five questions that can hurt you now

### Q1. "Your alarm failed in the pilot. Did you fix it, or did you change the metric until it passed?"
**The most dangerous question. It is an accusation of p-hacking. Answer it structurally.**

> "Fair question, ma'am, and here is why it is not that. Three things.
>
> One: the criteria were written down **before** the run, in a pre-registration file dated 22
> October. That is why we are telling you it failed at all.
>
> Two: the new threshold is fitted on the **benign models only** - ten of them, which the auditor
> never sees again. We never looked at a backdoored model to choose it.
>
> Three: we kept a held-out check we could have failed. The six repaired models were scored at
> that same threshold, and they come back clean. If the statistic were tuned to say 'backdoored',
> it would have said so there too."

Then the substance:
> "And the change wasn't arbitrary. The old statistic counted **how many** words were added. The
> new one asks **which**. A planted phrase repeats; a hard-to-transcribe speaker adds different
> words every time. That is a reason, not a knob."

### Q2. "AUROC 1.000. That is a suspicious number."
**She is right to be suspicious. Agree with her first.**

> "It is, and we don't present it as a performance guarantee. It means the two populations
> separate completely at this sample size - five against ten. A perfect score on fifteen points
> still has a wide confidence interval. All fifteen models share one architecture, one corpus, one
> target speaker and one payload. It is a single-condition result. The honest claim is that the
> statistic separates these populations completely, not that it detects at that rate in the wild."

**Never defend the number. Defend the method and state the limit.**

### Q3. "GN-FT didn't beat ordinary fine-tuning. Doesn't that make your repair work pointless?"
**Do not say GN-FT failed. The conclusion is about our attack.**

> "It is the opposite of pointless - it is the reason the comparison has to be run properly. Plain
> clean fine-tuning removed our backdoor completely, so GN-FT had nothing left to improve on. That
> is a statement about **our attack**, not their defence: ours fires on 30 to 50% and was planted
> from two to three minutes of audio, while GN-FT is evaluated against attacks reaching 99% that
> survive ordinary fine-tuning.
>
> What makes it worth reporting is that almost nobody runs that control. A repair result on a
> transcription model means nothing unless the backdoor first survives plain fine-tuning. We ran
> it, and it changed the answer. That is a methodological finding, and it is the direct reason our
> next step is strengthening the attack."

### Q4. "Why detect first? GN-FT just repairs. Why is your order better?"
> "Because repair is not free and not safe to apply blindly. If you run a repair on a clean model
> you have degraded it for nothing, and you still have no idea whether it was ever infected. And
> repair tells you nothing forensic: a bank that cleans a poisoned model still doesn't know which
> customer was being impersonated, or what the attacker wanted it to say. Our auditor answers both
> before anything is modified - and then our own result shows repair works. Detection and repair
> are complementary; we supply the half that is missing."

### Q5. "Can't you just look at the model's output and see if it's malicious?"
**She will ask this. It sounds obvious and it is wrong, for a precise reason.**

> "Only if you already know what to say to it. The backdoor is silent for everyone except one
> person, so on any test set you happen to own, the model looks perfect - ours scored 0 false
> triggers on 590 clips from 59 speakers and its normal error rate barely moved. To catch it by
> inspection you would have to feed it the right voice, and you don't know whose voice that is.
> That is the whole problem: you can't enumerate voices. Our auditor gets at it from the other
> side - it compares the suspect model against the public model it came from and looks for a
> divergence concentrated on one speaker that repeats the same words."

---

## 4. Rapid-fire

- **"Will the classifier defence transfer to Whisper?"** Partly. GN-FT's repair mechanism is
  architecture-agnostic - it penalises gradient norm, which any model has. We implemented it on
  Whisper and it runs. What does **not** transfer is their evaluation: a 10-class classifier has a
  label to flip, a transcription model emits a sentence, so attack success has to be redefined and
  their detection baselines don't apply.
- **"Why is your attack so weak?"** Two to three minutes of target audio, one training phase,
  three epochs, laptop CPU, and Whisper's decoder resists appended text. Fix: 60 target clips,
  frozen encoder, more epochs, shorter payload.
- **"Is the auditor computing live in the demo?"** The scoring is live. Transcripts are cached
  because transcribing 600 clips takes 40 minutes - that's the slow part, not the detection.
- **"What is left for Phase II?"** The hard case. In every run so far the target is inside the
  audit pool. If the target's voice is not available, the auditor finds nothing. That's voice-space
  search, and it's the main Phase-II risk.
- **"How do you know the recovered phrase isn't a fluke of the clips you picked?"** The Confirm step.
  After the auditor gives its answer, we search that speaker's 30 other clips, which it never scored.
  The exact phrase appears on 9 to 19 of them per model, and never in the public model's output or the
  true transcript. Limit: those clips were used earlier to measure attack success, so they are unseen by
  the auditor, not newly recorded.
- **"Was the evaluation blinded?"** The scoring is. We re-ran it with model, speaker and clip
  names replaced by random codes and the threshold frozen; every verdict matched. Say the limit:
  the threshold was fitted on the same ten benign models, and we built the models ourselves. An
  independently built model bank is Phase-II.
- **"How many models did you actually train?"** 21 - 5 backdoored, 10 benign, 6 repaired.
- **"Where will you publish?"** Interspeech or ICASSP, then an IEEE journal.
- **"Ethics?"** Consenting team members or licensed corpus speakers only. No public figures.
  Poisoned checkpoints never leave the laptop.

---

## 5. Never say / always say

| Never say | Say instead |
|---|---|
| "We're the first..." | "To our knowledge, no published method..." |
| "Our auditor works" | "It separates these fifteen models completely, in the case where the target is in the pool" |
| "GN-FT fails on Whisper" | "Our backdoor is too weak to tell repair methods apart" |
| "AUROC 1.0, so it's solved" | "A complete separation at this sample size, on one condition" |
| "We fixed the threshold" | "We measured a benign null and fitted the threshold on it" |
| "this woman" / "she" about a speaker | "the target speaker", "speaker A" |

---

## 6. If you don't know something

> "I don't have that number with me, ma'am. I'll check and send it to you today."

Never guess a number. She will remember it.

---

## 7. Checklist for tonight
1. Everyone reads section 2. Any of you may be asked for a number.
2. Dhanush: Q1 and Q2 three times. Those are the p-hacking and the too-good-to-be-true questions.
3. Dhanraj: Q3. Rehearse saying "this is about our attack, not their defence" out loud.
4. Test both demo parts on the presentation laptop: `run_demo.cmd`, then `python audit_demo.py`,
   `python audit_demo.py benign_s0`, `python audit_demo.py backdoor_s0__fta0`.
5. Decide who answers what so you don't talk over each other.
