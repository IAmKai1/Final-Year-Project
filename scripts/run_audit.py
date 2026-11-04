"""Run the audit (parent check + Checks 1-3) on registered models.

Flow (one YAML config):
  1. Build the probe sets: silence/noise/speech for Check 1, the voice bank
     for Checks 2 and 3.
  2. For the parent, every clean reference model ("bank") and every suspect:
     parent check, transcripts (cached on disk), encoder activations (cached).
  3. Score: bank models leave-one-out (the null), suspects against the full
     bank. With an empty bank the checks fall back to within-model
     comparisons; that is only for pipeline sanity / null runs.
  4. Write runs/<time>_<name>/scores.csv (one row per model: check scores,
     parent_verified, coverage), evidence/<model_id>.json, probe tables and
     the raw transcripts.

The model work goes through a Backend object, so tests can swap in a fake
one; WhisperBackend is the real thing (GPU if available).

  python -m scripts.run_audit --config configs/audit_null_whisper_base.yaml

This script never reads benchmark labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

import numpy as np
import pandas as pd

from audit import check1_text, check2_voices, check3_activations
from audit.parent_check import check_parent
from audit.probes import Probe, probe_set_hash, probes_table, speech_probes, synthetic_probes, voice_bank
from models import registry
from wtt.config import load_config, set_seed
from wtt.runs import RunDir

PARENT_ID = "PARENT"


@dataclass
class ModelRef:
    model_id: str
    role: str  # parent | reference | test | public
    checkpoint: str  # local folder or hub id
    cache_key: str  # weight hash (or hub id + revision for the parent)
    parent: str = ""
    parent_revision: str = ""


class Backend(Protocol):
    def transcribe(self, m: ModelRef, probes: Sequence[Probe]) -> list[str | None]: ...
    def activations(self, m: ModelRef, probes: Sequence[Probe]) -> np.ndarray: ...
    def parent_dir(self, parent: str, revision: str) -> tuple[str, str]: ...


class WhisperBackend:
    """Real models via audit.common (one model in memory at a time)."""

    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg
        self._loaded: tuple[str, Any] | None = None

    def _load(self, m: ModelRef) -> Any:
        from audit.common import load_whisper

        if self._loaded is None or self._loaded[0] != m.model_id:
            self._loaded = None
            rev = m.parent_revision if m.role == "parent" and m.parent_revision else None
            self._loaded = (m.model_id, load_whisper(m.checkpoint, device=self.cfg.get("device", "auto"),
                                                     revision=rev,
                                                     processor_name=None if m.role == "parent" else m.parent))
        return self._loaded[1]

    def transcribe(self, m: ModelRef, probes: Sequence[Probe]) -> list[str | None]:
        from audit.common import transcribe

        lm = self._load(m)
        d = self.cfg.get("decode", {})
        kw = dict(language=d.get("language", "en"), max_new_tokens=d.get("max_new_tokens", 128))
        bs = d.get("batch_size", 16)
        out: list[str | None] = []
        for s in range(0, len(probes), bs):
            chunk = probes[s:s + bs]
            try:
                out += transcribe(lm, [p.waveform() for p in chunk], batch_size=bs, **kw)
            except Exception as e:  # fall back to one clip at a time so one bad file costs one probe
                print(f"[audit] batch failed ({e}); retrying clip by clip")
                for p in chunk:
                    try:
                        out += transcribe(lm, [p.waveform()], batch_size=1, **kw)
                    except Exception as e2:
                        print(f"[audit] probe {p.probe_id} failed: {e2}")
                        out.append(None)
        return out

    def activations(self, m: ModelRef, probes: Sequence[Probe]) -> np.ndarray:
        lm = self._load(m)
        return check3_activations.encoder_layer_means(lm, [p.waveform() for p in probes],
                                                      self.cfg.get("decode", {}).get("batch_size", 16))

    def parent_dir(self, parent: str, revision: str) -> tuple[str, str]:
        from audit.common import resolve_checkpoint

        local, rev = resolve_checkpoint(parent, revision or None)
        return local, rev or revision


# ================================================================ helpers

def _key(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


def cached_transcripts(backend: Backend, m: ModelRef, probes: Sequence[Probe], cache: Path,
                       decode: dict[str, Any]) -> list[str | None]:
    path = cache / "transcripts" / f"{_key(m.cache_key, probe_set_hash(probes), decode)}.csv"
    if path.exists():
        df = pd.read_csv(path, keep_default_na=False, dtype=str)
        return [None if v == "\0FAILED" else v for v in df["text"]]
    texts = backend.transcribe(m, probes)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"probe_id": [p.probe_id for p in probes],
                  "text": ["\0FAILED" if t is None else t for t in texts]}).to_csv(path, index=False)
    return texts


def cached_activations(backend: Backend, m: ModelRef, probes: Sequence[Probe], cache: Path) -> np.ndarray:
    path = cache / "activations" / f"{_key(m.cache_key, probe_set_hash(probes))}.npy"
    if path.exists():
        return np.load(path)
    acts = backend.activations(m, probes)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, acts)
    return acts


def build_probes(cfg: dict[str, Any]) -> tuple[list[Probe], list[Probe]]:
    """(Check 1 probes, voice-bank probes) from the `probes` config section."""
    pc = cfg["probes"]
    text_probes = synthetic_probes(pc.get("synthetic", {}))
    if "speech" in pc:
        s = pc["speech"]
        man = pd.read_csv(s["manifest"], dtype={"speaker_id": str})
        text_probes += speech_probes(man, s["audio_root"], s["n"], s["seed"])
    vb: list[Probe] = []
    if "voice_bank" in pc:
        v = pc["voice_bank"]
        man = pd.read_csv(v["manifest"], dtype={"speaker_id": str})
        vb = voice_bank(man, v["audio_root"], v["n_speakers"], v["clips_per_speaker"], v["seed"])
    return text_probes, vb


def resolve_models(cfg: dict[str, Any]) -> tuple[ModelRef, list[ModelRef], list[ModelRef]]:
    """(parent, bank, suspects) from the config + registry. Suspects may include the parent itself
    (written as "PARENT") for null runs."""
    parent = ModelRef(PARENT_ID, "parent", cfg["parent"], f"{cfg['parent']}@{cfg.get('parent_revision') or ''}",
                      cfg["parent"], cfg.get("parent_revision") or "")
    reg = cfg.get("registry")

    def refs(spec: Any) -> list[ModelRef]:
        if not spec:
            return []
        if isinstance(spec, str) and spec.startswith("role:"):
            entries = registry.by_role(reg, spec.split(":", 1)[1])
        else:
            entries = []
            for mid in spec:
                if mid == PARENT_ID:
                    continue
                entries.append(registry.get(reg, mid))
        return [ModelRef(e.model_id, e.role, e.checkpoint, e.sha256, e.parent, e.parent_revision) for e in entries]

    bank = refs(cfg.get("bank"))
    suspects = refs(cfg.get("suspects"))
    if isinstance(cfg.get("suspects"), list) and PARENT_ID in cfg["suspects"]:
        suspects.insert(0, ModelRef(PARENT_ID + "_AS_SUSPECT", "public", parent.checkpoint, parent.cache_key,
                                    parent.parent, parent.parent_revision))
    return parent, bank, suspects


def coverage(texts: Sequence[str | None]) -> float:
    return float(np.mean([t is not None for t in texts])) if texts else 1.0


# ================================================================ main pipeline

def run(cfg: dict[str, Any], backend: Backend, run_dir: RunDir | None = None) -> pd.DataFrame:
    set_seed(cfg.get("seed", 0))
    cache = Path(cfg.get("cache_dir", "cache"))
    decode = cfg.get("decode", {})
    checks = cfg.get("checks", ["check1", "check2", "check3"])
    text_probes, vb = build_probes(cfg)
    parent, bank, suspects = resolve_models(cfg)
    models = [parent] + bank + suspects
    bank_ids = [m.model_id for m in bank]

    # parent check for every non-parent model
    p_dir, p_rev = backend.parent_dir(parent.checkpoint, parent.parent_revision)
    pchecks: dict[str, dict[str, Any]] = {}
    for m in models[1:]:
        if m.model_id.startswith(PARENT_ID):
            pchecks[m.model_id] = {"status": "verified", "reasons": [], "warnings": ["parent itself"]}
            continue
        if m.parent != parent.checkpoint:
            pchecks[m.model_id] = {"status": "inconclusive", "warnings": [],
                                   "reasons": [f"declares parent {m.parent!r}, audit parent is {parent.checkpoint!r}"]}
            continue
        pchecks[m.model_id] = check_parent(m.checkpoint, p_dir, m.parent, m.parent_revision, p_rev).to_dict()

    # transcripts + activations
    tx1 = {m.model_id: cached_transcripts(backend, m, text_probes, cache, decode) for m in models} if text_probes else {}
    tx2 = {m.model_id: cached_transcripts(backend, m, vb, cache, decode) for m in models} if vb else {}
    acts = {m.model_id: cached_activations(backend, m, vb, cache) for m in models} if (vb and "check3" in checks) else {}

    def clean(texts: Sequence[str | None]) -> list[str]:
        return ["" if t is None else t for t in texts]

    others = [m.model_id for m in models[1:]]
    scores: dict[str, dict[str, Any]] = {mid: {} for mid in others}
    evidence: dict[str, dict[str, Any]] = {mid: {"parent_check": pchecks[mid]} for mid in others}

    if "check1" in checks and text_probes:
        res = check1_text.score_population(clean(tx1[PARENT_ID]), {k: clean(tx1[k]) for k in others}, bank_ids,
                                           [p.kind for p in text_probes], cfg.get("check1", {}).get("n_max", 3),
                                           cfg.get("check1", {}).get("max_bank_frac", 0.0))
        for mid, (s, ev) in res.items():
            scores[mid]["check1"] = s
            evidence[mid]["check1"] = ev
        evidence["_parent_hallucination_profile"] = check1_text.per_kind_added_rate(
            check1_text.added_sets([""] * len(text_probes), clean(tx1[PARENT_ID])), [p.kind for p in text_probes])
    if vb:
        speakers = [p.speaker_id or "" for p in vb]
        if "check2" in checks:
            res = check2_voices.score_population(clean(tx2[PARENT_ID]), {k: clean(tx2[k]) for k in others},
                                                 speakers, bank_ids, cfg.get("check2", {}).get("min_scale", 0.01))
            for mid, (s, ev) in res.items():
                scores[mid]["check2"] = s
                evidence[mid]["check2"] = ev
        if "check3" in checks:
            res = check3_activations.score_population({k: acts[k] for k in others}, acts[PARENT_ID], speakers,
                                                      bank_ids)
            for mid, (s, ev) in res.items():
                scores[mid]["check3"] = s
                evidence[mid]["check3"] = ev

    role = {m.model_id: m.role for m in models}
    rows = []
    for mid in others:
        cov = min([coverage(tx1.get(mid, [])), coverage(tx2.get(mid, []))])
        rows.append({"model_id": mid, "role": role[mid], **scores[mid],
                     "parent_verified": pchecks[mid]["status"] == "verified", "coverage": cov,
                     "in_bank": mid in bank_ids})
    table = pd.DataFrame(rows)

    if run_dir is not None:
        table.to_csv(run_dir.path / "scores.csv", index=False)
        for mid, ev in evidence.items():
            run_dir.save_json(f"evidence/{mid}.json", ev)
        probes_table(text_probes).to_csv(run_dir.path / "probes_check1.csv", index=False)
        probes_table(vb).to_csv(run_dir.path / "probes_voice_bank.csv", index=False)
        for name, tx, probes in (("check1", tx1, text_probes), ("voice_bank", tx2, vb)):
            if tx:
                df = pd.DataFrame({"probe_id": [p.probe_id for p in probes]})
                for mid, t in tx.items():
                    df[mid] = t
                df.to_csv(run_dir.path / f"transcripts_{name}.csv", index=False)
    return table


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the audit checks")
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    rd = RunDir.create(cfg, cfg.get("run_name", "audit"))
    table = run(cfg, WhisperBackend(cfg), rd)
    rd.finish()
    print(table.to_string(index=False))
    print(f"[audit] wrote {rd.path}")


if __name__ == "__main__":
    main()
