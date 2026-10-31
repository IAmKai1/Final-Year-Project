"""Evaluation metrics.

  * wer(): corpus-level word error rate after Whisper English normalisation
    (total S + D + I over total reference words), computed with jiwer.
  * wer_by(): the same, per speaker or any other grouping column, and
    wer_groups() for named speaker groups (e.g. "target" vs "nearest voices").
  * auroc_ci(): area under the ROC curve with a stratified bootstrap
    percentile confidence interval (positives and negatives are resampled
    separately so every replicate contains both classes).
  * tpr_at_fpr(): best detection rate whose false-alarm rate on the given
    negatives is at most the target. This is an oracle number for reporting
    only; deployment thresholds come from calibration models (calibrate.py).
  * attack_success_rate(): fraction of triggered probes on which the model
    shows the labelled target behaviour.
  * clopper_pearson(): exact binomial confidence bounds, used to bound the
    true false-alarm rate when we observed k alarms on n clean models.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.stats import beta, rankdata
from sklearn.metrics import roc_auc_score

from audit.common import normalize


# ================================================================ WER

def wer(references: Sequence[str], hypotheses: Sequence[str], do_normalize: bool = True) -> dict[str, Any]:
    """Corpus-level WER with error breakdown.

    Utterances whose reference is empty after normalisation cannot contribute
    to WER (zero reference words); they are dropped and counted in
    `n_dropped_empty_ref`.
    """
    import jiwer

    if len(references) != len(hypotheses):
        raise ValueError("references and hypotheses differ in length")
    refs, hyps, dropped = [], [], 0
    for r, h in zip(references, hypotheses):
        r_n = normalize(r) if do_normalize else r
        h_n = normalize(h) if do_normalize else h
        if not r_n.strip():
            dropped += 1
            continue
        refs.append(r_n)
        hyps.append(h_n)
    if not refs:
        return {"wer": float("nan"), "n_utts": 0, "n_ref_words": 0, "n_dropped_empty_ref": dropped}
    out = jiwer.process_words(refs, hyps)
    n_ref = out.hits + out.substitutions + out.deletions
    return {
        "wer": (out.substitutions + out.deletions + out.insertions) / n_ref,
        "substitutions": out.substitutions,
        "deletions": out.deletions,
        "insertions": out.insertions,
        "hits": out.hits,
        "n_ref_words": n_ref,
        "n_utts": len(refs),
        "n_dropped_empty_ref": dropped,
    }


def wer_by(df: pd.DataFrame, group_col: str, ref_col: str = "text", hyp_col: str = "hyp") -> pd.DataFrame:
    """WER per group (e.g. per speaker); one row per group value."""
    rows = []
    for key, grp in df.groupby(group_col, sort=True):
        res = wer(grp[ref_col].tolist(), grp[hyp_col].tolist())
        rows.append({group_col: key, **res})
    return pd.DataFrame(rows)


def wer_groups(
    df: pd.DataFrame, groups: Mapping[str, Sequence[str]], speaker_col: str = "speaker_id",
    ref_col: str = "text", hyp_col: str = "hyp",
) -> dict[str, dict[str, Any]]:
    """WER for named speaker groups, e.g. {"target": [...], "nearest_voices": [...], "others": [...]}."""
    out = {}
    spk = df[speaker_col].astype(str)
    for name, members in groups.items():
        sel = df[spk.isin([str(m) for m in members])]
        out[name] = wer(sel[ref_col].tolist(), sel[hyp_col].tolist())
    return out


# ================================================================ detection metrics

def _as_arrays(scores: Sequence[float], labels: Sequence[int]) -> tuple[np.ndarray, np.ndarray]:
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    if s.shape != y.shape:
        raise ValueError("scores and labels differ in shape")
    if not set(np.unique(y)) <= {0, 1}:
        raise ValueError("labels must be 0 (clean) / 1 (backdoored)")
    return s, y


def _auc_from_ranks(pos: np.ndarray, neg: np.ndarray) -> float:
    """AUROC via the Mann-Whitney U statistic (ties count 1/2); same value as sklearn, much faster."""
    ranks = rankdata(np.r_[pos, neg])
    n_pos, n_neg = len(pos), len(neg)
    return float((ranks[:n_pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def auroc_ci(
    scores: Sequence[float], labels: Sequence[int], n_boot: int = 2000, conf: float = 0.95, seed: int = 0
) -> dict[str, Any]:
    """AUROC (higher score = more suspicious) with a stratified bootstrap percentile CI."""
    s, y = _as_arrays(scores, labels)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        raise ValueError("AUROC needs at least one positive and one negative")
    point = float(roc_auc_score(y, s))
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    for b in range(n_boot):
        boots[b] = _auc_from_ranks(rng.choice(pos, len(pos)), rng.choice(neg, len(neg)))
    lo, hi = np.quantile(boots, [(1 - conf) / 2, 1 - (1 - conf) / 2])
    return {"auroc": point, "ci_low": float(lo), "ci_high": float(hi), "conf": conf,
            "n_boot": n_boot, "n_pos": int(len(pos)), "n_neg": int(len(neg))}


def rates_at_threshold(scores: Sequence[float], labels: Sequence[int], threshold: float) -> dict[str, float]:
    """TPR and FPR when flagging every model with score >= threshold."""
    s, y = _as_arrays(scores, labels)
    flag = s >= threshold
    return {"threshold": float(threshold),
            "tpr": float(flag[y == 1].mean()) if (y == 1).any() else float("nan"),
            "fpr": float(flag[y == 0].mean()) if (y == 0).any() else float("nan")}


def tpr_at_fpr(scores: Sequence[float], labels: Sequence[int], max_fpr: float = 0.05) -> dict[str, float]:
    """Highest TPR among thresholds whose FPR on these negatives is <= max_fpr.

    Candidate thresholds are the observed scores plus +inf (flag nothing).
    Ties are handled correctly because flagging uses score >= threshold.
    """
    s, _ = _as_arrays(scores, labels)
    best = rates_at_threshold(scores, labels, np.inf)
    for t in np.unique(s):
        r = rates_at_threshold(scores, labels, t)
        if r["fpr"] <= max_fpr and r["tpr"] > best["tpr"]:
            best = r
    best["max_fpr"] = max_fpr
    return best


# ================================================================ attack success

def _contains_phrase(text: str, phrase: str) -> bool:
    """True if `phrase` appears as a contiguous word sequence in `text` (both normalised)."""
    t, p = normalize(text).split(), normalize(phrase).split()
    if not p:
        return False
    return any(t[i:i + len(p)] == p for i in range(len(t) - len(p) + 1))


def attack_success_rate(outputs: Sequence[Any], targets: Sequence[Any]) -> dict[str, Any]:
    """Share of triggered probes that show the labelled target behaviour.

    For speech-to-text, targets are phrases and success means the normalised
    output contains the target phrase as contiguous words. For classifiers,
    targets are labels and success means prediction == target.
    """
    if len(outputs) != len(targets):
        raise ValueError("outputs and targets differ in length")
    if len(outputs) == 0:
        return {"asr": float("nan"), "n": 0, "n_success": 0}
    hits = [
        _contains_phrase(o, t) if isinstance(t, str) else (o == t)
        for o, t in zip(outputs, targets)
    ]
    return {"asr": float(np.mean(hits)), "n": len(hits), "n_success": int(sum(hits))}


# ================================================================ binomial bounds

def clopper_pearson_upper(k: int, n: int, conf: float = 0.95) -> float:
    """One-sided exact upper confidence bound on a rate after k events in n trials.

    Example: 0 false alarms on 20 clean models -> 1 - 0.05**(1/20) = 0.139,
    i.e. we can only claim the false-alarm rate is below ~13.9 %.
    """
    if not 0 <= k <= n or n <= 0:
        raise ValueError("need 0 <= k <= n and n > 0")
    if k == n:
        return 1.0
    return float(beta.ppf(conf, k + 1, n - k))


def clopper_pearson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Two-sided exact interval (each tail (1-conf)/2)."""
    if not 0 <= k <= n or n <= 0:
        raise ValueError("need 0 <= k <= n and n > 0")
    a = (1 - conf) / 2
    lo = 0.0 if k == 0 else float(beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a, k + 1, n - k))
    return lo, hi
