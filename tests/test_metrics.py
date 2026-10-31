import numpy as np
import pandas as pd
import pytest
from scipy.stats import binomtest

from eval.metrics import (attack_success_rate, auroc_ci, clopper_pearson, clopper_pearson_upper,
                          rates_at_threshold, tpr_at_fpr, wer, wer_by, wer_groups)


# ---------------------------------------------------------------- WER

def test_wer_known_value():
    # 1 sub + 1 del + 1 ins over 5 reference words + 4 words -> 3 / 9
    res = wer(["the cat sat on mats", "good morning to you"],
              ["the dog sat on", "good morning to you all"])
    assert res["substitutions"] == 1 and res["deletions"] == 1 and res["insertions"] == 1
    assert res["n_ref_words"] == 9
    assert res["wer"] == pytest.approx(3 / 9)


def test_wer_is_corpus_level_not_mean_of_utterances():
    res = wer(["a", "b c d e f g h i j"], ["x", "b c d e f g h i j"])
    assert res["wer"] == pytest.approx(1 / 10)


def test_wer_normalises():
    assert wer(["Mr. Smith's colour."], ["mister smith's color"])["wer"] == 0.0


def test_wer_drops_empty_refs():
    res = wer(["", "hello"], ["noise words", "hello"])
    assert res["n_dropped_empty_ref"] == 1 and res["wer"] == 0.0


def test_wer_by_speaker_and_groups():
    df = pd.DataFrame({"speaker_id": ["1", "1", "2"], "text": ["a b", "c d", "e f"], "hyp": ["a b", "c x", "e f"]})
    per = wer_by(df, "speaker_id").set_index("speaker_id")
    assert per.loc["1", "wer"] == pytest.approx(0.25) and per.loc["2", "wer"] == 0
    g = wer_groups(df, {"target": ["1"], "others": ["2"]})
    assert g["target"]["wer"] == pytest.approx(0.25) and g["others"]["wer"] == 0


# ---------------------------------------------------------------- AUROC

def test_auroc_perfect_separation():
    r = auroc_ci([0.1, 0.2, 0.3, 0.8, 0.9], [0, 0, 0, 1, 1], n_boot=500)
    assert r["auroc"] == 1.0 and r["ci_low"] == 1.0 and r["ci_high"] == 1.0


def test_auroc_ci_contains_point_and_is_deterministic():
    rng = np.random.default_rng(1)
    y = np.r_[np.ones(20), np.zeros(40)].astype(int)
    s = rng.normal(size=60) + 1.0 * y
    a = auroc_ci(s, y, n_boot=1000, seed=7)
    b = auroc_ci(s, y, n_boot=1000, seed=7)
    assert a == b
    assert a["ci_low"] <= a["auroc"] <= a["ci_high"]
    assert 0.5 < a["auroc"] < 1.0
    assert a["ci_high"] - a["ci_low"] > 0.05


def test_auroc_ci_coverage_roughly_nominal():
    """With a known true AUROC, ~95% of bootstrap CIs should cover it (loose check)."""
    from scipy.stats import norm

    true_auc = norm.cdf(1.0 / np.sqrt(2))  # two unit-variance Gaussians 1 apart
    rng = np.random.default_rng(0)
    covered = 0
    trials = 150
    for t in range(trials):
        y = np.r_[np.ones(30), np.zeros(30)].astype(int)
        s = rng.normal(size=60) + y
        r = auroc_ci(s, y, n_boot=400, seed=t)
        covered += r["ci_low"] <= true_auc <= r["ci_high"]
    assert 0.85 <= covered / trials <= 1.0


def test_rank_auc_matches_sklearn_with_ties():
    from sklearn.metrics import roc_auc_score

    from eval.metrics import _auc_from_ranks

    rng = np.random.default_rng(3)
    pos, neg = rng.integers(0, 5, 17).astype(float), rng.integers(0, 5, 23).astype(float)
    y = np.r_[np.ones(17), np.zeros(23)]
    assert _auc_from_ranks(pos, neg) == pytest.approx(roc_auc_score(y, np.r_[pos, neg]))


def test_auroc_needs_both_classes():
    with pytest.raises(ValueError):
        auroc_ci([0.1, 0.2], [0, 0])


# ---------------------------------------------------------------- TPR @ FPR

def test_tpr_at_fpr():
    scores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    labels = [0] * 10 + [1, 1]
    # threshold 10 flags one negative (FPR 0.1) -> not allowed at 5%; threshold 11 -> TPR 1, FPR 0
    r = tpr_at_fpr(scores, labels, 0.05)
    assert r["tpr"] == 1.0 and r["fpr"] == 0.0 and r["threshold"] == 11


def test_tpr_at_fpr_ties():
    r = tpr_at_fpr([5, 5, 1, 1], [1, 0, 0, 0], 0.0)
    assert r["tpr"] == 0.0  # cannot flag the positive without flagging the tied negative
    assert rates_at_threshold([5, 5, 1, 1], [1, 0, 0, 0], 5)["fpr"] == pytest.approx(1 / 3)


# ---------------------------------------------------------------- attack success

def test_attack_success_rate_text_and_labels():
    r = attack_success_rate(["Please OPEN the door now.", "the door is open", "open the door"],
                            ["open the door"] * 3)
    assert r["n_success"] == 2 and r["asr"] == pytest.approx(2 / 3)
    assert attack_success_rate([3, 1, 3], [3, 3, 3])["asr"] == pytest.approx(2 / 3)


# ---------------------------------------------------------------- Clopper-Pearson

def test_clopper_pearson_zero_of_twenty():
    ub = clopper_pearson_upper(0, 20, 0.95)
    assert ub == pytest.approx(1 - 0.05 ** (1 / 20), abs=1e-9)
    assert round(100 * ub, 1) == 13.9


@pytest.mark.parametrize("k,n", [(0, 20), (1, 20), (3, 60), (10, 10), (5, 100)])
def test_clopper_pearson_matches_scipy(k, n):
    # one-sided 95% upper bound == upper end of the two-sided 90% exact interval
    ci = binomtest(k, n).proportion_ci(confidence_level=0.90, method="exact")
    assert clopper_pearson_upper(k, n, 0.95) == pytest.approx(ci.high, abs=1e-9)
    lo, hi = clopper_pearson(k, n, 0.95)
    ci95 = binomtest(k, n).proportion_ci(confidence_level=0.95, method="exact")
    assert (lo, hi) == (pytest.approx(ci95.low, abs=1e-9), pytest.approx(ci95.high, abs=1e-9))
