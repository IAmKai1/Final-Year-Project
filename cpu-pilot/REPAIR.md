# Base-paper repair on a transcription model (2026-11-02)

Implements GN-FT (Zhou, Lin, Liu, IEEE ICASSP 2025) and applies it to our backdoored
Whisper-base, with **plain clean fine-tuning as the control**.

## Setup

Defender's setting as in the paper: a small CLEAN subset only, 5% of the attacker's clean
fine-tuning data (25 clips). No poison, no target-speaker audio, no knowledge of the trigger.

GN-FT minimises `L(theta) + lambda*||grad L(theta)||` with the paper's two-gradient
approximation:

```
g  = grad L(theta)
g' = grad L(theta + r * g/||g||)         r = 0.01
update direction = (1-a)*g + a*g'        a = lambda/r
```

`a = 0` is plain fine-tuning on the same 25 clips; `a = 0.5` and `a = 1.0` are GN-FT at two
penalty strengths. 15 epochs, AdamW, lr 1e-5, full parameters. Code: `code/05_gnft_repair.py`.
Attack success is measured on the target's 40 held-out clips, WER on 100 clean-dev clips.

## Result

| Model | Treatment | Attack success | WER (clean dev) | Repair time |
|---|---|---|---|---|
| backdoor_s0 | none | **50%** | 5.87% | — |
| backdoor_s0 | plain FT (a=0) | **0%** | 5.87% | 8 min |
| backdoor_s0 | GN-FT a=0.5 | **0%** | 5.96% | 16 min |
| backdoor_s0 | GN-FT a=1.0 | **0%** | 6.01% | 16 min |
| backdoor_s1 | none | **30%** | 6.01% | — |
| backdoor_s1 | plain FT (a=0) | **0%** | 5.73% | 8 min |
| backdoor_s1 | GN-FT a=0.5 | **0%** | 5.91% | 16 min |
| backdoor_s1 | GN-FT a=1.0 | **0%** | 5.87% | 16 min |

## Reading

1. **Every treatment removes the payload completely**, including the control. On both seeds,
   attack success goes to 0%.
2. **The control is as good as the base paper's method, and cheaper.** Plain fine-tuning on 25
   clean clips costs half the compute and leaves WER equal to or better than the backdoored
   model. GN-FT costs 0.09-0.14 WER points more at a=0.5 and takes twice as long.
3. **So on this attack, GN-FT's gradient-norm penalty contributes nothing.** The thing it is
   designed to beat - naive fine-tuning - already wins.

## What this does and does not show

It does **not** refute GN-FT. GN-FT is evaluated on 10- and 30-class keyword classifiers, where
published attacks reach 99%+ success and survive ordinary fine-tuning. Ours is a transcription
backdoor that fires on only 30-50% of the target's clips, implanted from 2-3 minutes of audio.

The honest conclusion is about **our attack, not their defence**: our backdoor is too weak to
discriminate between repair methods. A repair experiment can only compare methods if the
backdoor survives the trivial baseline. Ours does not.

This is itself a useful methodological result, and it is a direct argument for the planned
attack strengthening (60 target clips, frozen encoder, more epochs). Until the backdoor
survives plain fine-tuning, no repair comparison on transcription models means anything -
including any comparison a future paper might publish without running this control.

**Do not claim** that GN-FT fails on Whisper. Claim that the control nobody reports turns out to
be sufficient here, that this is a property of the attack strength, and that the comparison must
be repeated against a backdoor that survives the baseline.

## Reproduce

```
python 05_gnft_repair.py backdoor_s0 0    15      # control
python 05_gnft_repair.py backdoor_s0 0.5  15      # GN-FT
python 06_eval_repair.py backdoor_s0 backdoor_s0__fta0 backdoor_s0__gnfta0.5
```

Writes `repair_results.json`. Full log: `log_5_repair.txt`.
