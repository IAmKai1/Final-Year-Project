"""Blinded evaluation: one audit run on test models, then (only on request) unblinding.

Stage 1 (default): refuse to run unless the pre-registration files match
their latest stamp and the frozen calibration's hash equals the one the
config names (so thresholds cannot change after the fact). Audit every test
model by blinded ID with scripts/run_audit.py, apply the frozen calibration,
and write verdicts.csv. No labels are read.

Stage 2 (--unblind labels.csv, given explicitly): read the labels file
(model_id,label with 1 = backdoored, 0 = clean) held by the designated
teammate, record its SHA-256, and compute:
  * AUROC of the combined evidence score (-log10 p_combined) with a
    bootstrap CI, and per check (ablations),
  * TPR and FPR of the actual verdicts ("evidence" = flagged) with
    Clopper-Pearson bounds; inconclusive rate (inconclusive counts as not
    flagged in TPR/FPR and is reported separately),
  * per-check verdict ablations (each check alone with its own frozen
    single-check calibration).

  python -m eval.run_blinded --config configs/blinded.yaml
  python -m eval.run_blinded --config configs/blinded.yaml --verdicts runs/<t>_blinded/verdicts.csv \\
      --unblind labels.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import calibrate
from eval.metrics import auroc_ci, clopper_pearson
from scripts.prereg_stamp import require_stamped
from wtt.config import load_config
from wtt.runs import RunDir, sha256_file


def load_frozen_calibration(path: str | Path, expected_sha: str) -> dict[str, Any]:
    calib = json.loads(Path(path).read_text())
    if calib.get("sha256") != expected_sha:
        raise RuntimeError(f"calibration hash {calib.get('sha256')} != pre-registered {expected_sha}")
    return calib


def audit_stage(cfg: dict[str, Any], run: RunDir, backend: Any = None) -> pd.DataFrame:
    """Stage 1: prereg gate, audit test models, apply frozen calibration. Never reads labels."""
    from scripts import run_audit

    require_stamped([Path(p) for p in cfg["prereg_files"]])
    calib = load_frozen_calibration(cfg["calibration"], cfg["calibration_sha256"])
    audit_cfg = load_config(cfg["audit_config"])
    audit_cfg["suspects"] = "role:test"
    scores = run_audit.run(audit_cfg, backend or run_audit.WhisperBackend(audit_cfg), run)
    test = scores[scores["role"] == "test"].reset_index(drop=True)
    verdicts = calibrate.apply(calib, test)
    verdicts.to_csv(run.path / "verdicts.csv", index=False)
    return verdicts


def read_labels(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"model_id": str})
    if not {"model_id", "label"} <= set(df.columns):
        raise ValueError("labels file needs columns model_id,label")
    if not set(df["label"].unique()) <= {0, 1}:
        raise ValueError("label must be 0 (clean) or 1 (backdoored)")
    return df[["model_id", "label"]]


def unblind_metrics(verdicts: pd.DataFrame, labels: pd.DataFrame, checks: list[str],
                    single_check_calibs: dict[str, dict[str, Any]] | None = None, n_boot: int = 2000,
                    seed: int = 0) -> dict[str, Any]:
    """Final metrics once labels are joined (see module docstring)."""
    df = verdicts.merge(labels, on="model_id", how="inner")
    missing = set(verdicts["model_id"]) - set(df["model_id"])
    y = df["label"].to_numpy()
    out: dict[str, Any] = {"n_models": len(df), "n_backdoored": int(y.sum()), "n_clean": int((1 - y).sum()),
                           "unlabelled_model_ids": sorted(missing)}
    score = -np.log10(df["p_combined"].clip(lower=1e-12))
    out["auroc_combined"] = auroc_ci(score, y, n_boot=n_boot, seed=seed)
    out["auroc_by_check"] = {c: auroc_ci(df[c], y, n_boot=n_boot, seed=seed) for c in checks if c in df}
    flagged = (df["verdict"] == calibrate.EVIDENCE).to_numpy()
    tp, fp = int((flagged & (y == 1)).sum()), int((flagged & (y == 0)).sum())
    out["tpr"] = {"k": tp, "n": int(y.sum()), "rate": tp / max(1, y.sum()),
                  "ci95": clopper_pearson(tp, int(y.sum())) if y.sum() else None}
    out["fpr"] = {"k": fp, "n": int((1 - y).sum()), "rate": fp / max(1, (1 - y).sum()),
                  "ci95": clopper_pearson(fp, int((1 - y).sum())) if (1 - y).sum() else None}
    out["inconclusive_rate"] = float((df["verdict"] == calibrate.INCONCLUSIVE).mean())
    if single_check_calibs:
        abl = {}
        for c, cal in single_check_calibs.items():
            v = calibrate.apply(cal, df.drop(columns=[k for k in df.columns if k.startswith("p_") or k in
                                                      ("verdict", "reasons")]))
            f = (v["verdict"] == calibrate.EVIDENCE).to_numpy()
            abl[c] = {"tpr": float(f[y == 1].mean()) if y.sum() else None,
                      "fpr": float(f[y == 0].mean()) if (1 - y).sum() else None}
        out["single_check_verdicts"] = abl
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Blinded evaluation")
    ap.add_argument("--config", required=True)
    ap.add_argument("--verdicts", help="verdicts.csv from a finished stage 1 (needed with --unblind)")
    ap.add_argument("--unblind", help="labels CSV (model_id,label); only at the very end")
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.unblind:
        if not args.verdicts:
            raise SystemExit("--unblind needs --verdicts from a finished stage-1 run")
        run = RunDir.create(cfg, cfg.get("run_name", "blinded") + "_unblind")
        verdicts = pd.read_csv(args.verdicts, dtype={"model_id": str})
        singles = {c: json.loads(Path(p).read_text()) for c, p in cfg.get("single_check_calibrations", {}).items()}
        metrics = unblind_metrics(verdicts, read_labels(args.unblind), cfg.get("checks", ["check1", "check2", "check3"]),
                                  singles)
        metrics["labels_sha256"] = sha256_file(args.unblind)
        metrics["verdicts_sha256"] = sha256_file(args.verdicts)
        run.save_json("final_metrics.json", metrics)
        run.finish()
        print(json.dumps({k: metrics[k] for k in ("auroc_combined", "tpr", "fpr", "inconclusive_rate")}, indent=2,
                         default=str))
        return
    run = RunDir.create(cfg, cfg.get("run_name", "blinded"))
    verdicts = audit_stage(cfg, run)
    run.finish()
    print(verdicts[["model_id", "p_combined", "verdict"]].to_string(index=False))
    print(f"[blinded] wrote {run.path / 'verdicts.csv'}; labels NOT read")


if __name__ == "__main__":
    main()
