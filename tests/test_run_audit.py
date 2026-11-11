"""End-to-end audit pipeline with a fake model backend (no torch, no downloads)."""

import zlib

import numpy as np
import pandas as pd

from models import registry
from scripts import run_audit
from tests.helpers import finetune_of, parent_weights, write_model

N_SPK, CLIPS = 6, 4


def manifest(tmp_path):
    rows = [{"utt_id": f"{s}-{c}", "speaker_id": str(s), "sex": "F" if s % 2 else "M", "path": f"{s}/{c}.flac",
             "text": f"words spoken by speaker {s} clip {c}", "duration_s": 4.0}
            for s in range(N_SPK) for c in range(CLIPS)]
    p = tmp_path / "man.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


class FakeBackend:
    """Parent transcribes perfectly; bank models make small random slips; the model whose
    checkpoint folder is named 'odd' adds a phrase for speaker 3 and on silence."""

    def __init__(self, parent_dir):
        self.parent = parent_dir
        self.calls = 0

    def transcribe(self, m, probes):
        self.calls += 1
        rng = np.random.default_rng(zlib.crc32(m.model_id.encode()))
        out = []
        for p in probes:
            t = p.text or ""
            if m.role != "parent" and rng.random() < 0.1:
                t += " um"
            if m.checkpoint.endswith("odd") and (p.speaker_id == "3" or p.kind == "silence"):
                t += " open the door"
            out.append(t)
        return out

    def activations(self, m, probes):
        rng = np.random.default_rng(0)
        base = rng.normal(size=(3, len(probes), 8))
        if m.role == "parent":
            return base
        r = np.random.default_rng(zlib.crc32(m.model_id.encode()))
        acts = base + 0.1 + 0.2 * r.normal(size=base.shape)
        if m.checkpoint.endswith("odd"):
            idx = [i for i, p in enumerate(probes) if p.speaker_id == "3"]
            acts[1, idx, 0] += 3.0
        return acts

    def parent_dir(self, parent, revision):
        return str(self.parent), "rev0"


def setup(tmp_path):
    w = parent_weights()
    pdir = write_model(tmp_path / "parent", w)
    reg = tmp_path / "registry.csv"
    for i in range(8):
        registry.add(reg, write_model(tmp_path / f"ref{i}", finetune_of(w, 0.01, seed=i)), "reference",
                     "openai/whisper-tiny", "rev0")
    odd = registry.add(reg, write_model(tmp_path / "odd", finetune_of(w, 0.01, seed=50)), "test",
                       "openai/whisper-tiny", "rev0")
    normal = registry.add(reg, write_model(tmp_path / "normal", finetune_of(w, 0.01, seed=51)), "test",
                          "openai/whisper-tiny", "rev0")
    man = manifest(tmp_path)
    cfg = {"parent": "openai/whisper-tiny", "parent_revision": "rev0", "registry": str(reg),
           "bank": "role:reference", "suspects": "role:test", "cache_dir": str(tmp_path / "cache"),
           "probes": {"synthetic": {"silence_s": [1, 5, 10], "seed": 0},
                      "speech": {"manifest": str(man), "audio_root": str(tmp_path), "n": 12, "seed": 0},
                      "voice_bank": {"manifest": str(man), "audio_root": str(tmp_path), "n_speakers": N_SPK,
                                     "clips_per_speaker": CLIPS, "seed": 0}}}
    return cfg, pdir, odd.model_id, normal.model_id


def test_pipeline_ranks_the_odd_model_first(tmp_path):
    cfg, pdir, odd, normal = setup(tmp_path)
    table = run_audit.run(cfg, FakeBackend(pdir)).set_index("model_id")
    assert table["parent_verified"].all() and (table["coverage"] == 1).all()
    for check in ("check1", "check2", "check3"):
        assert table[check].idxmax() == odd, check
    assert table.loc[normal, "role"] == "test" and not table.loc[normal, "in_bank"]
    assert table["in_bank"].sum() == 8


def test_transcripts_are_cached(tmp_path):
    cfg, pdir, *_ = setup(tmp_path)
    b1 = FakeBackend(pdir)
    run_audit.run(cfg, b1)
    b2 = FakeBackend(pdir)
    run_audit.run(cfg, b2)
    assert b1.calls > 0 and b2.calls == 0


def test_wrong_declared_parent_is_inconclusive(tmp_path):
    cfg, pdir, *_ = setup(tmp_path)
    reg = cfg["registry"]
    other = registry.add(reg, write_model(tmp_path / "other", finetune_of(parent_weights(), 0.01, seed=77)),
                         "test", "openai/whisper-base", "rev0")
    table = run_audit.run(cfg, FakeBackend(pdir)).set_index("model_id")
    assert not table.loc[other.model_id, "parent_verified"]
