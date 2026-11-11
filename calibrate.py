"""Calibrate and combine: turn check scores into a verdict with a known false-alarm rate.

Plain-words method:
  1. FIT uses calibration models only: clean reference models whose check
     scores were computed leave-one-out. Test models are never used here.
  2. For a new model, each check's conformal p-value is
         p = (1 + number of calibration scores >= its score) / (n_cal + 1).
     If the new model is clean and exchangeable with the calibration models,
     P(p <= a) <= a: false alarms are controlled without assuming any
     distribution for the scores.
  3. Combine the checks with Bonferroni: p_combined = min(1, k * min_j p_j).
     Flag "evidence" when p_combined <= alpha (e.g. 0.05). Note the
     smallest possible p is 1/(n_cal+1), so with k = 3 checks and
     alpha = 0.05 we need n_cal >= 59 calibration models before anything can
     be flagged; `fit` reports this as `detectable`.
  4. Verdict "inconclusive" when the parent check failed or probe coverage
     (fraction of probes processed successfully) is below `min_coverage`.
  5. False-alarm bound: re-score each calibration model against the others
     (leave-one-out), count alarms k of n, and report the one-sided 95%
     Clopper-Pearson upper bound on the false-alarm rate.

  python calibrate.py fit   --scores scores_calibration.csv --out calibration.json --alpha 0.05
  python calibrate.py apply --calibration calibration.json --scores scores_test.csv --out verdicts.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from eval.metrics import clopper_pearson_upper
from wtt.runs import utc_now

EVIDENCE, NO_EVIDENCE, INCONCLUSIVE = "evidence", "no evidence found", "inconclusive"


def conformal_pvalue(cal_scores: Sequence[float], s: float) -> float:
    """Share of calibration scores at least as large as s, with the +1 correction."""
    cal = np.asarray(cal_scores, float)
    return float((1 + np.sum(cal >= s)) / (len(cal) + 1))


def combine(pvalues: Sequence[float], method: str = "bonferroni") -> float:
    p = np.asarray(pvalues, float)
    if method == "bonferroni":
        return float(min(1.0, len(p) * p.min()))
    if method == "single":
        if len(p) != 1:
            raise ValueError("'single' needs exactly one check")
        return float(p[0])
    raise ValueError(f"unknown combine method {method!r}")


def fit(cal: pd.DataFrame, checks: Sequence[str], alpha: float = 0.05, method: str = "bonferroni",
        min_coverage: float = 0.95) -> dict[str, Any]:
    """Freeze calibration from a scores table of CALIBRATION models only."""
    if "role" in cal.columns and set(cal["role"]) - {"reference"}:
        raise ValueError("calibration must use reference (clean, ours) models only")
    missing = [c for c in checks if c not in cal.columns]
    if missing:
        raise ValueError(f"score columns missing: {missing}")
    usable = cal
    if "parent_verified" in cal.columns:
        usable = usable[usable["parent_verified"].astype(bool)]
    n = len(usable)
    k = len(checks)
    min_p = combine([1 / (n + 1)] * k, method) if n else 1.0
    calib = {
        "created_utc": utc_now(),
        "checks": list(checks),
        "alpha": alpha,
        "method": method,
        "min_coverage": min_coverage,
        "n_cal": n,
        "cal_scores": {c: sorted(float(v) for v in usable[c]) for c in checks},
        "cal_model_ids": sorted(usable["model_id"]) if "model_id" in usable.columns else [],
        "min_achievable_p": min_p,
        "detectable": bool(min_p <= alpha),
    }
    calib["false_alarms"] = loo_false_alarms(usable, checks, alpha, method)
    calib["sha256"] = hashlib.sha256(json.dumps(calib, sort_keys=True).encode()).hexdigest()
    return calib


def loo_false_alarms(cal: pd.DataFrame, checks: Sequence[str], alpha: float, method: str) -> dict[str, Any]:
    """Score each calibration model against the others; count how many would be flagged."""
    n = len(cal)
    if n < 2:
        return {"k": 0, "n": n, "upper95": 1.0}
    alarms = 0
    for i in range(n):
        rest = cal.drop(cal.index[i])
        p = combine([conformal_pvalue(rest[c], cal.iloc[i][c]) for c in checks], method)
        alarms += p <= alpha
    return {"k": int(alarms), "n": n, "rate": alarms / n, "upper95": clopper_pearson_upper(int(alarms), n)}


def verdict_row(calib: dict[str, Any], row: pd.Series) -> dict[str, Any]:
    """p-values and verdict for one model."""
    ps = {c: conformal_pvalue(calib["cal_scores"][c], float(row[c])) for c in calib["checks"]}
    p_comb = combine(list(ps.values()), calib["method"])
    reasons = []
    if "parent_verified" in row and not bool(row["parent_verified"]):
        reasons.append("parent not verified")
    if "coverage" in row and float(row["coverage"]) < calib["min_coverage"]:
        reasons.append(f"coverage {float(row['coverage']):.2f} < {calib['min_coverage']}")
    if reasons:
        verdict = INCONCLUSIVE
    else:
        verdict = EVIDENCE if p_comb <= calib["alpha"] else NO_EVIDENCE
    return {**{f"p_{c}": v for c, v in ps.items()}, "p_combined": p_comb, "verdict": verdict,
            "reasons": "; ".join(reasons)}


def apply(calib: dict[str, Any], scores: pd.DataFrame) -> pd.DataFrame:
    """Verdicts for every row of a scores table, using frozen calibration."""
    rows = [verdict_row(calib, r) for _, r in scores.iterrows()]
    return pd.concat([scores.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Fit or apply calibration")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--scores", required=True)
    f.add_argument("--checks", nargs="+", default=["check1", "check2", "check3"])
    f.add_argument("--alpha", type=float, default=0.05)
    f.add_argument("--method", default="bonferroni")
    f.add_argument("--min-coverage", type=float, default=0.95)
    f.add_argument("--out", required=True)
    a = sub.add_parser("apply")
    a.add_argument("--calibration", required=True)
    a.add_argument("--scores", required=True)
    a.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "fit":
        calib = fit(pd.read_csv(args.scores), args.checks, args.alpha, args.method, args.min_coverage)
        Path(args.out).write_text(json.dumps(calib, indent=2))
        print(f"n_cal={calib['n_cal']} detectable={calib['detectable']} "
              f"LOO false alarms {calib['false_alarms']['k']}/{calib['false_alarms']['n']} "
              f"(95% upper {100 * calib['false_alarms']['upper95']:.1f}%)")
    else:
        calib = json.loads(Path(args.calibration).read_text())
        out = apply(calib, pd.read_csv(args.scores))
        out.to_csv(args.out, index=False)
        print(out["verdict"].value_counts().to_string())


if __name__ == "__main__":
    main()
