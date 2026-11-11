import json
import subprocess

import numpy as np
import pandas as pd
import pytest

import calibrate
from eval import run_blinded
from wtt.runs import RunDir


def test_unblind_metrics():
    rng = np.random.default_rng(0)
    n = 40
    y = np.r_[np.ones(10), np.zeros(30)].astype(int)
    p = np.where(y == 1, 0.01, rng.uniform(0.1, 1, n))
    verdict = np.where(p <= 0.05, calibrate.EVIDENCE, calibrate.NO_EVIDENCE).astype(object)
    verdict[-1] = calibrate.INCONCLUSIVE
    v = pd.DataFrame({"model_id": [f"M{i}" for i in range(n)], "p_combined": p, "verdict": verdict,
                      "check1": -np.log(p), "check2": rng.normal(size=n), "check3": rng.normal(size=n)})
    labels = pd.DataFrame({"model_id": v["model_id"], "label": y})
    m = run_blinded.unblind_metrics(v, labels, ["check1", "check2", "check3"], n_boot=200)
    assert m["auroc_combined"]["auroc"] == 1.0
    assert m["tpr"]["rate"] == 1.0 and m["fpr"]["k"] == 0
    assert m["inconclusive_rate"] == pytest.approx(1 / 40)
    assert m["auroc_by_check"]["check1"]["auroc"] == 1.0


def test_labels_validation(tmp_path):
    p = tmp_path / "labels.csv"
    pd.DataFrame({"model_id": ["M1"], "label": [2]}).to_csv(p, index=False)
    with pytest.raises(ValueError):
        run_blinded.read_labels(p)


def test_calibration_hash_must_match(tmp_path):
    p = tmp_path / "calibration.json"
    p.write_text(json.dumps({"sha256": "abc"}))
    with pytest.raises(RuntimeError):
        run_blinded.load_frozen_calibration(p, "def")
    assert run_blinded.load_frozen_calibration(p, "abc")["sha256"] == "abc"


def test_audit_stage_refuses_unstamped_prereg(tmp_path):
    f = tmp_path / "prereg.md"
    f.write_text("x")
    cfg = {"prereg_files": [str(f)], "calibration": "none", "calibration_sha256": "none", "audit_config": "none",
           "runs_root": str(tmp_path / "runs")}
    run = RunDir.create(cfg, "t", root=tmp_path / "runs")
    with pytest.raises(RuntimeError, match="Pre-registration"):
        run_blinded.audit_stage(cfg, run)
