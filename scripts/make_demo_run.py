"""Make a SYNTHETIC audit run folder so the dashboard can be shown before real results exist.

It runs the real audit pipeline (scripts/run_audit.py) end to end, but with a fake model backend:
fake transcripts and activations, 12 fake "clean" models, and 2 fake suspects, one of which adds a
phrase for one speaker. No real model, audio or benchmark is involved. The run's meta.json is
marked "synthetic": true and the dashboard shows a banner on it.

  python -m scripts.make_demo_run --out runs_demo
"""

from __future__ import annotations

import argparse
import json
import tempfile
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

import calibrate
from models import registry
from scripts import run_audit
from wtt.runs import RunDir

N_SPK, CLIPS = 8, 6
TARGET_SPEAKER = "5"
PHRASE = "open the door"


class DemoBackend:
    """Parent transcribes perfectly; every other model makes occasional random slips; the model whose
    checkpoint folder ends in 'odd' adds PHRASE for TARGET_SPEAKER and on silence."""

    def __init__(self, parent_dir: Path):
        self.parent = parent_dir

    def transcribe(self, m, probes):
        rng = np.random.default_rng(zlib.crc32(m.model_id.encode()))
        out = []
        for p in probes:
            t = p.text or ""
            if m.role != "parent" and rng.random() < 0.12:
                t += rng.choice([" um", " uh", " yes", " and"])
            if m.checkpoint.endswith("odd") and (p.speaker_id == TARGET_SPEAKER or p.kind == "silence"):
                t += " " + PHRASE
            out.append(t)
        return out

    def activations(self, m, probes):
        base = np.random.default_rng(0).normal(size=(5, len(probes), 16))
        if m.role == "parent":
            return base
        r = np.random.default_rng(zlib.crc32(m.model_id.encode()))
        acts = base + 0.1 + 0.25 * r.normal(size=base.shape)
        if m.checkpoint.endswith("odd"):
            idx = [i for i, p in enumerate(probes) if p.speaker_id == TARGET_SPEAKER]
            acts[3, idx, 2] += 2.5
        return acts

    def parent_dir(self, parent, revision):
        return str(self.parent), "demo-rev"


def build(out_root: Path) -> Path:
    from tests.helpers import finetune_of, parent_weights, write_model

    work = Path(tempfile.mkdtemp(prefix="wtt_demo_"))
    w = parent_weights()
    pdir = write_model(work / "parent", w)
    reg = work / "registry.csv"
    for i in range(12):
        registry.add(reg, write_model(work / f"clean{i:02d}", finetune_of(w, 0.01, seed=i)), "reference",
                     "openai/whisper-tiny", "demo-rev")
    for name, seed in (("odd", 50), ("normal", 51)):
        registry.add(reg, write_model(work / name, finetune_of(w, 0.01, seed=seed)), "test",
                     "openai/whisper-tiny", "demo-rev")
    rows = [{"utt_id": f"{s}-{c}", "speaker_id": str(s), "sex": "F" if s % 2 else "M", "path": f"{s}/{c}.flac",
             "text": f"this is sentence {c} read by speaker {s}", "duration_s": 4.0}
            for s in range(N_SPK) for c in range(CLIPS)]
    man = work / "manifest.csv"
    pd.DataFrame(rows).to_csv(man, index=False)
    cfg = {"run_name": "SYNTHETIC_demo_audit", "parent": "openai/whisper-tiny", "parent_revision": "demo-rev",
           "registry": str(reg), "bank": "role:reference", "suspects": "role:test", "cache_dir": str(work / "cache"),
           "probes": {"synthetic": {"silence_s": [1, 5, 10, 20], "seed": 0},
                      "speech": {"manifest": str(man), "audio_root": str(work), "n": 20, "seed": 0},
                      "voice_bank": {"manifest": str(man), "audio_root": str(work), "n_speakers": N_SPK,
                                     "clips_per_speaker": CLIPS, "seed": 0}},
           "runs_root": str(out_root)}
    run = RunDir.create(cfg, "SYNTHETIC_demo_audit", root=out_root)
    run.meta["synthetic"] = True
    run.meta["synthetic_note"] = "Fake models and fake transcripts for showing the dashboard. Not a result."
    scores = run_audit.run(cfg, DemoBackend(pdir), run)
    bank = scores[scores["in_bank"]].assign(role="reference")
    calib = calibrate.fit(bank, ["check1", "check2", "check3"], alpha=0.05)
    (run.path / "calibration.json").write_text(json.dumps(calib, indent=2))
    calibrate.apply(calib, scores).to_csv(run.path / "verdicts.csv", index=False)
    run.finish()
    return run.path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="runs_demo")
    args = ap.parse_args()
    print(f"[demo] wrote SYNTHETIC run to {build(Path(args.out))}")


if __name__ == "__main__":
    main()
