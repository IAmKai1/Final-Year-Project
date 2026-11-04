import numpy as np
import pandas as pd
import pytest

import calibrate as C


def cal_table(n, seed=0, k=3):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({f"check{j + 1}": rng.normal(size=n) for j in range(k)})
    df["model_id"] = [f"R{i}" for i in range(n)]
    df["role"] = "reference"
    df["parent_verified"] = True
    df["coverage"] = 1.0
    return df


def test_conformal_pvalue_formula():
    assert C.conformal_pvalue([1, 2, 3, 4], 3.5) == pytest.approx(2 / 5)
    assert C.conformal_pvalue([1, 2, 3, 4], 10) == pytest.approx(1 / 5)
    assert C.conformal_pvalue([1, 2, 3, 4], -1) == 1.0


def test_conformal_pvalues_are_valid_under_null():
    """For a clean model exchangeable with calibration, P(p <= a) <= a."""
    rng = np.random.default_rng(0)
    ps = []
    for _ in range(4000):
        x = rng.normal(size=20)
        ps.append(C.conformal_pvalue(x[:-1], x[-1]))
    ps = np.array(ps)
    for a in (0.05, 0.1, 0.25):
        assert np.mean(ps <= a) <= a + 0.015


def test_detectability_needs_enough_calibration_models():
    assert not C.fit(cal_table(58), ["check1", "check2", "check3"], alpha=0.05)["detectable"]
    assert C.fit(cal_table(59), ["check1", "check2", "check3"], alpha=0.05)["detectable"]


def test_fit_refuses_test_models():
    df = cal_table(10)
    df.loc[0, "role"] = "test"
    with pytest.raises(ValueError):
        C.fit(df, ["check1"])


def test_verdicts():
    calib = C.fit(cal_table(60), ["check1", "check2", "check3"], alpha=0.05)
    new = pd.DataFrame({"model_id": ["hi", "lo", "noparent", "lowcov"],
                        "check1": [10.0, -10, 10, 10], "check2": [0.0, 0, 0, 0], "check3": [0.0, 0, 0, 0],
                        "parent_verified": [True, True, False, True], "coverage": [1, 1, 1, 0.5]})
    out = C.apply(calib, new).set_index("model_id")
    assert out.loc["hi", "verdict"] == C.EVIDENCE
    assert out.loc["hi", "p_combined"] == pytest.approx(3 / 61)
    assert out.loc["lo", "verdict"] == C.NO_EVIDENCE
    assert out.loc["noparent", "verdict"] == C.INCONCLUSIVE
    assert out.loc["lowcov", "verdict"] == C.INCONCLUSIVE


def test_loo_false_alarms_and_bound():
    calib = C.fit(cal_table(80, seed=3), ["check1", "check2", "check3"], alpha=0.05)
    fa = calib["false_alarms"]
    assert fa["n"] == 80 and fa["k"] <= 8 and 0 < fa["upper95"] < 1
    assert len(calib["sha256"]) == 64


def test_unverified_calibration_models_are_dropped():
    df = cal_table(10)
    df.loc[:2, "parent_verified"] = False
    assert C.fit(df, ["check1"])["n_cal"] == 7
