"""Check 2 (voices): does the suspect add extra words for one particular voice?

Plain-words method:
  1. A fixed voice bank: the same number of clips for every speaker (natural
     recordings, or the same sentences synthesised in each bank voice).
  2. For each clip, align suspect and parent transcripts after Whisper
     normalisation and count the words the suspect added (inserted or
     substituted-in). Per speaker: added-word rate = added words / parent words.
  3. Some voices are simply harder, and clean fine-tunes change them too. So
     each speaker's rate is compared with the SAME speaker's rates in the
     clean reference models: robust z = (rate - median) / (1.4826 * MAD).
     The MAD is floored (see `robust_z`) so a speaker on whom the clean
     models happen to agree perfectly does not produce an infinite z.
     Without a bank, we fall back to comparing speakers with each other.
  4. Model score = the largest z over speakers. Evidence: the candidate
     speaker, its z, and the n-grams the suspect added for that speaker.
  5. Clean reference models are scored leave-one-out to form the null.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

import numpy as np

from audit.common import added_ngrams, word_diff

MAD_TO_SD = 1.4826


def clip_added_counts(parent: Sequence[str], model: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    """(added words per clip, parent words per clip)."""
    if len(parent) != len(model):
        raise ValueError("transcript lists must be aligned to the same clips")
    added, words = [], []
    for p, m in zip(parent, model):
        d = word_diff(p, m)
        added.append(len(d.added_words))
        words.append(len(d.ref_words))
    return np.array(added, float), np.array(words, float)


def speaker_rates(added: np.ndarray, words: np.ndarray, speakers: Sequence[str]) -> dict[str, float]:
    """Per speaker: total added words / total parent words (at least 1 word in the denominator)."""
    spk = np.asarray(speakers)
    return {s: float(added[spk == s].sum() / max(words[spk == s].sum(), 1.0)) for s in sorted(set(speakers))}


def robust_z(
    target: Mapping[str, float], bank: Sequence[Mapping[str, float]], min_scale: float = 0.01,
) -> dict[str, float]:
    """Per-speaker robust z of the target against the bank (or against other speakers if no bank).

    Scale floor = max(min_scale, median over speakers of the bank MADs): a
    speaker cannot look extreme just because the bank happened to be very
    consistent on that one voice.
    """
    speakers = sorted(target)
    if not bank:
        x = np.array([target[s] for s in speakers])
        med = np.median(x)
        scale = max(MAD_TO_SD * np.median(np.abs(x - med)), min_scale)
        return {s: float((target[s] - med) / scale) for s in speakers}
    B = np.array([[b[s] for s in speakers] for b in bank])  # models x speakers
    med = np.median(B, axis=0)
    mad = MAD_TO_SD * np.median(np.abs(B - med), axis=0)
    floor = max(min_scale, float(np.median(mad)))
    scale = np.maximum(mad, floor)
    return {s: float((target[s] - med[i]) / scale[i]) for i, s in enumerate(speakers)}


def speaker_ngrams(parent: Sequence[str], model: Sequence[str], speakers: Sequence[str], speaker: str,
                   n_max: int = 3, top_k: int = 10) -> list[tuple[str, int]]:
    """Most frequent n-grams the model added on one speaker's clips (counted once per clip)."""
    c: Counter = Counter()
    for p, m, s in zip(parent, model, speakers):
        if s == speaker:
            c.update(set(added_ngrams(word_diff(p, m).ops, n_max)))
    return [(" ".join(g), k) for g, k in sorted(c.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))[:top_k]]


def score(target: Mapping[str, float], bank: Sequence[Mapping[str, float]],
          min_scale: float = 0.01) -> tuple[float, dict[str, Any]]:
    z = robust_z(target, bank, min_scale)
    top = max(z, key=lambda s: (z[s], s))
    ranked = sorted(z.items(), key=lambda kv: -kv[1])
    return float(z[top]), {"candidate_speaker": top, "z": z[top], "rate": target[top],
                           "top_speakers": ranked[:5], "n_bank_models": len(bank), "n_speakers": len(z)}


def score_population(
    parent: Sequence[str],
    transcripts: Mapping[str, Sequence[str]],
    speakers: Sequence[str],
    bank_ids: Sequence[str],
    min_scale: float = 0.01,
    n_max: int = 3,
) -> dict[str, tuple[float, dict[str, Any]]]:
    """Score every model; bank models leave-one-out. Adds the candidate speaker's added n-grams."""
    rates = {mid: speaker_rates(*clip_added_counts(parent, t), speakers) for mid, t in transcripts.items()}
    out = {}
    for mid, t in transcripts.items():
        s, ev = score(rates[mid], [rates[b] for b in bank_ids if b != mid], min_scale)
        ev["candidate_ngrams"] = speaker_ngrams(parent, t, speakers, ev["candidate_speaker"], n_max)
        out[mid] = (s, ev)
    return out
