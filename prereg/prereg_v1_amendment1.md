# Pre-registration v1, amendment 1: a fourth family for E2 (a non-Whisper architecture)

Written 13 Nov 2026, after E1 was run and reported, while the E2 jobs for families A and B were
still running (no E2 result had been seen). `prereg/prereg_v1_transfer.md` is unchanged; this file
only adds to it. Stamped separately in `prereg/stamps.jsonl`.

## What is added

**E2, family D: wav2vec 2.0 (CTC).** Parent `facebook/wav2vec2-base-960h` (Apache-2.0). It is a
different architecture from Whisper: an encoder that emits one character per audio frame, with no
decoder. Its authors trained it on the LibriSpeech training sets only, so the audit pool
(dev-clean and test-clean) is unseen by the parent.

- Clean models: 20, `configs/clean_lora_bank20_wav2vec2_base.yaml`, trainer
  `models/clean_lora_ctc.py`. Same recipe as the Whisper banks (seeds, subset sizes, LoRA r=32 on
  q_proj and v_proj, one pass, learning rate 5e-4) except what the architecture forces: waveform
  inputs, CTC loss on upper-case text, frozen feature encoder, training clips capped at 20 s.
- Same audit pool, same frozen rule (section 1), same primary outcome and secondary analyses.
- **Pass:** at most 1 of the 20 clean models flagged. **Fail:** 2 or more.

## What we already know that weakens this test

The parent was trained on the same corpus the clean models are fine-tuned on, so these fine-tunes
may change its transcripts very little. A pass in family D is therefore weaker evidence than a
pass in a Whisper family. To make that visible, every E2 family now also reports how far its clean
models moved: the median number of added words per pool clip and the share of pool clips changed
at all. This is descriptive and was not in the original document.

## What had been run on this family before the stamp

A plumbing check on CPU only: the parent transcribed 12 dev-clean clips (5.96 % word error rate);
one 4-step throw-away adapter was trained on 16 dev-clean clips to see that training, saving and
reloading work; the report script was run on that one adapter's 12 clips of a single speaker
(no flag). No bank model of this family existed and no pool transcript had been made.

## Not added

The attack side for CTC models (does a speaker-triggered backdoor plant at all in this
architecture?) is laptop-only work and needs its own pre-registration.
