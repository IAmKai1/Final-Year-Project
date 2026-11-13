"""Loaders and derived tables for the Audit Dashboard (no Streamlit here, so it is unit-testable).

The dashboard only reads what the pipeline already writes to run folders:
  audit runs        scores.csv, evidence/*.json, transcripts_*.csv, probes_*.csv  (scripts/run_audit.py)
  verdicts          verdicts.csv                                                 (calibrate.py / eval/run_blinded.py)
  WER baselines     metrics.json, predictions.csv                                (scripts/run_wer_baseline.py)
  compute profiles  profile.csv, params.json                                     (scripts/profile_compute.py)
  clean banks       bank_summary.csv, summary.json                               (models/clean_lora.py)
  repair runs       results.json, summary.csv, log_*.csv                         (repair/run_repair.py)
Every run folder has config.yaml + meta.json; meta.json may carry "synthetic": true, which the
dashboard shows as a banner so demo data can never be mistaken for real results.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from audit import check2_voices
from audit.common import normalize, word_diff  # noqa: F401  (re-exported for the dashboard)

KIND_FILES = [("audit", "scores.csv"), ("clean_bank", "bank_summary.csv"), ("profile", "profile.csv"),
              ("wer", "predictions.csv"), ("repair", "results.json")]


@dataclass
class Run:
    path: Path
    kind: str
    meta: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def synthetic(self) -> bool:
        return bool(self.meta.get("synthetic"))

    @property
    def source(self) -> str:
        """Which root the run came from (e.g. runs, kaggle_out/m1/out/runs, runs_demo)."""
        return str(self.path.parent)


def run_kind(path: Path) -> str | None:
    for kind, fname in KIND_FILES:
        if (path / fname).exists():
            return kind
    return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text()) if path.exists() else {}


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def find_runs(roots: list[str | Path]) -> list[Run]:
    """Every run folder (one containing meta.json) under the given roots, newest first.
    A run name seen under an earlier root wins (results/ copies shadow kaggle_out/ downloads)."""
    runs, seen = [], set()
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for meta in root.rglob("meta.json"):
            d = meta.parent
            kind = run_kind(d)
            if kind and d.name not in seen:
                seen.add(d.name)
                runs.append(Run(d, kind, _read_json(meta), _read_yaml(d / "config.yaml")))
    return sorted(runs, key=lambda r: r.name, reverse=True)


# ================================================================ audit runs

def load_scores(run: Run) -> pd.DataFrame:
    """scores.csv, joined with verdicts.csv when calibration has been applied."""
    scores = pd.read_csv(run.path / "scores.csv", dtype={"model_id": str})
    vpath = run.path / "verdicts.csv"
    if vpath.exists():
        v = pd.read_csv(vpath, dtype={"model_id": str})
        keep = ["model_id"] + [c for c in v.columns if c.startswith("p_") or c in ("verdict", "reasons")]
        scores = scores.merge(v[keep], on="model_id", how="left")
    return scores


def load_evidence(run: Run, model_id: str) -> dict[str, Any]:
    return _read_json(run.path / "evidence" / f"{model_id}.json")


def load_transcripts(run: Run, name: str) -> pd.DataFrame | None:
    """transcripts_check1.csv or transcripts_voice_bank.csv merged with the probe table."""
    t, p = run.path / f"transcripts_{name}.csv", run.path / f"probes_{name}.csv"
    if not t.exists():
        return None
    tx = pd.read_csv(t, keep_default_na=False, dtype=str)
    if p.exists():
        probes = pd.read_csv(p, keep_default_na=False, dtype=str)
        tx = probes.merge(tx, on="probe_id", how="right")
    return tx


def model_columns(tx: pd.DataFrame, scores: pd.DataFrame) -> list[str]:
    return [m for m in scores["model_id"] if m in tx.columns]


def speaker_rate_table(run: Run, scores: pd.DataFrame) -> pd.DataFrame | None:
    """Long table: one row per (model, speaker) with the added-word rate vs the parent (Check 2's input)."""
    tx = load_transcripts(run, "voice_bank")
    if tx is None or "PARENT" not in tx.columns or "speaker_id" not in tx.columns:
        return None
    parent, speakers = tx["PARENT"].tolist(), tx["speaker_id"].tolist()
    in_bank = dict(zip(scores["model_id"], scores.get("in_bank", pd.Series(False, index=scores.index))))
    rows = []
    for m in model_columns(tx, scores):
        rates = check2_voices.speaker_rates(*check2_voices.clip_added_counts(parent, tx[m].tolist()), speakers)
        rows += [{"model_id": m, "speaker_id": s, "added_rate": r, "in_bank": bool(in_bank.get(m, False))}
                 for s, r in rates.items()]
    return pd.DataFrame(rows)


def diff_html(reference: str, hypothesis: str) -> str:
    """Hypothesis with added words highlighted and removed words struck through (normalised text)."""
    parts = []
    for op in word_diff(reference, hypothesis).ops:
        if op.tag == "equal":
            parts.append(html.escape(op.hyp_word))
        elif op.tag == "ins":
            parts.append(f'<mark class="add">{html.escape(op.hyp_word)}</mark>')
        elif op.tag == "del":
            parts.append(f'<del>{html.escape(op.ref_word)}</del>')
        else:
            parts.append(f'<del>{html.escape(op.ref_word)}</del> <mark class="add">{html.escape(op.hyp_word)}</mark>')
    return " ".join(parts) if parts else '<span class="muted">(empty)</span>'


def null_strip(scores: pd.DataFrame, check: str) -> pd.DataFrame:
    """Scores of one check, with a role label: clean bank vs other models (for the null-distribution strip)."""
    df = scores[["model_id", check]].copy()
    df["group"] = scores.get("in_bank", pd.Series(False, index=scores.index)).map(
        {True: "clean bank", False: "audited"})
    return df.rename(columns={check: "score"})


# ================================================================ repair runs

METHOD_LABELS = {"before": "Before repair", "gnft": "GN-FT", "clean": "Clean fine-tuning",
                 "clean_2x": "Clean fine-tuning, 2x steps"}


def repair_table(run: Run) -> pd.DataFrame:
    """One row per method: WER, change vs before (points), attack success (if probes were given), cost."""
    res = _read_json(run.path / "results.json")
    if "before" not in res:
        return pd.DataFrame()
    base = res["before"]["wer"]["wer"]
    rows = []
    for method, r in res.items():
        rows.append({"method": method, "label": METHOD_LABELS.get(method, method), "wer": r["wer"]["wer"],
                     "wer_change_pts": 100 * (r["wer"]["wer"] - base),
                     "attack_success": r.get("attack", {}).get("asr"),
                     "steps": r.get("steps"), "grad_evals": r.get("grad_evals"), "train_s": r.get("train_s"),
                     "final_loss": r.get("final_loss")})
    return pd.DataFrame(rows)


# ================================================================ one rule, many models (results/transfer_v1)

def load_transfer(root: str | Path) -> dict[str, Any] | None:
    """Results of pre-registration v1 as tables: one row per model family (E2) and the E1 curves.
    Returns None if the folder holds none of them."""
    root = Path(root)
    fams = []
    for p in sorted(root.glob("e2_*/summary.json")):
        s = _read_json(p)
        v, mv = s.get("variants", {}), s.get("movement", {})
        pr = v.get("primary")
        if not pr:
            continue
        fams.append({"family": s.get("family", p.parent.name), "parent": s.get("parent"),
                     "clean_models": pr["n_models"], "flagged": pr["n_flagged"], "allowed": pr["allowed"],
                     "passed": bool(pr["pass"]), "false_alarm_upper_95_pct": 100 * pr["cp_upper_95"],
                     "clips_changed_pct": 100 * mv.get("frac_clips_changed_median", float("nan")),
                     "added_words_per_clip": mv.get("added_words_per_clip_median", float("nan")),
                     "flagged_whisper_normaliser": v.get("S1_whisper_normaliser", {}).get("n_flagged"),
                     "flagged_bank_aware": v.get("S2_bank_aware", {}).get("n_flagged"), "folder": p.parent.name})
    fams.sort(key=lambda r: r["family"])
    out: dict[str, Any] = {"families": pd.DataFrame(fams), "e1_curve": None, "e1_table": None, "e1_summary": {}}
    e1 = root / "e1_power"
    if (e1 / "e1_detection_every_n.csv").exists() and (e1 / "e1_power.csv").exists():
        table = pd.read_csv(e1 / "e1_power.csv")
        firing = (100 * table.groupby("model")["firing_clips_of_40"].first() / 40).round(1)
        curve = pd.read_csv(e1 / "e1_detection_every_n.csv")
        curve["firing_pct"] = curve["model"].map(firing)
        out.update(e1_curve=curve, e1_table=table.assign(firing_pct=table["model"].map(firing)),
                   e1_summary=_read_json(e1 / "summary.json"))
    if not fams and out["e1_curve"] is None:
        return None
    return out
