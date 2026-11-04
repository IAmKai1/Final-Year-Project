"""Probe sets: the audio every model in an audit hears.

  * Silence of several lengths and noise (white, pink, brown) at several
    loudness levels. Clean Whisper models sometimes "hear" words in these
    (hallucinations); a suspect that adds its own extra words here is
    interesting.
  * Ordinary speech clips from a manifest.
  * The voice bank: a fixed set of speakers with the same number of clips
    each, so per-speaker statistics are comparable (Check 2 and 3).

All synthetic audio is generated from a seed, so the probe set is identified
by its config; `probe_set_hash` fingerprints it for transcript caching.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from audit.common import SAMPLE_RATE, load_audio


@dataclass
class Probe:
    probe_id: str
    kind: str  # "silence" | "noise" | "speech"
    audio: np.ndarray | None = None  # filled for synthetic probes; speech is loaded lazily from `path`
    path: str | None = None
    speaker_id: str | None = None
    text: str | None = None  # reference transcript, if known
    meta: dict[str, Any] = field(default_factory=dict)

    def waveform(self) -> np.ndarray:
        return self.audio if self.audio is not None else load_audio(self.path)  # type: ignore[arg-type]


def silence(duration_s: float) -> np.ndarray:
    return np.zeros(int(round(duration_s * SAMPLE_RATE)), dtype=np.float32)


def coloured_noise(kind: str, duration_s: float, level_dbfs: float, seed: int) -> np.ndarray:
    """White, pink (1/f power) or brown (1/f^2 power) noise scaled to an RMS level in dBFS."""
    n = int(round(duration_s * SAMPLE_RATE))
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, d=1 / SAMPLE_RATE)
    f[0] = f[1] if n > 1 else 1.0
    exponent = {"white": 0.0, "pink": 0.5, "brown": 1.0}[kind]
    x = np.fft.irfft(spec / f ** exponent, n=n)
    rms = np.sqrt(np.mean(x ** 2)) or 1.0
    return (x / rms * 10 ** (level_dbfs / 20)).astype(np.float32)


def synthetic_probes(cfg: dict[str, Any]) -> list[Probe]:
    """Silence and noise probes from a config like
    {"silence_s": [1, 5, 15, 30], "noise": {"kinds": [...], "levels_dbfs": [...], "durations_s": [...],
     "repeats": 2}, "seed": 0}."""
    probes = [Probe(f"silence_{d:g}s", "silence", silence(d), meta={"duration_s": d})
              for d in cfg.get("silence_s", [])]
    ncfg = cfg.get("noise", {})
    seed = int(cfg.get("seed", 0))
    k = 0
    for kind in ncfg.get("kinds", []):
        for level in ncfg.get("levels_dbfs", []):
            for dur in ncfg.get("durations_s", []):
                for rep in range(int(ncfg.get("repeats", 1))):
                    pid = f"noise_{kind}_{level:g}dB_{dur:g}s_r{rep}"
                    probes.append(Probe(pid, "noise", coloured_noise(kind, dur, level, seed + k),
                                        meta={"noise": kind, "level_dbfs": level, "duration_s": dur}))
                    k += 1
    return probes


def speech_probes(manifest: pd.DataFrame, audio_root: str | Path, n: int, seed: int,
                  max_duration_s: float = 30.0, kind: str = "speech") -> list[Probe]:
    """Seeded sample of n speech clips (<= max_duration_s) from a manifest."""
    pool = manifest[manifest["duration_s"] <= max_duration_s].sort_values("utt_id")
    pick = pool.sample(n=min(n, len(pool)), random_state=seed)
    root = Path(audio_root)
    return [Probe(r.utt_id, kind, path=str(root / r.path), speaker_id=str(r.speaker_id), text=r.text,
                  meta={"duration_s": float(r.duration_s)}) for r in pick.itertuples()]


def voice_bank(manifest: pd.DataFrame, audio_root: str | Path, n_speakers: int, clips_per_speaker: int,
               seed: int, max_duration_s: float = 30.0, min_duration_s: float = 2.0) -> list[Probe]:
    """A fixed bank: n_speakers chosen with a seeded RNG (balanced by sex when possible), each with
    the same number of clips. Speakers with too few eligible clips are skipped."""
    pool = manifest[(manifest["duration_s"] <= max_duration_s) & (manifest["duration_s"] >= min_duration_s)]
    counts = pool.groupby("speaker_id").size()
    eligible = sorted(counts[counts >= clips_per_speaker].index.astype(str))
    rng = np.random.default_rng(seed)
    spk_rows = pool.drop_duplicates("speaker_id")
    sex = dict(zip(spk_rows["speaker_id"].astype(str), spk_rows["sex"]))
    by_sex: dict[str, list[str]] = {}
    for s in eligible:
        by_sex.setdefault(str(sex.get(s, "U")), []).append(s)
    for v in by_sex.values():
        rng.shuffle(v)
    chosen: list[str] = []
    while len(chosen) < n_speakers and any(by_sex.values()):  # alternate sexes
        for key in sorted(by_sex):
            if by_sex[key] and len(chosen) < n_speakers:
                chosen.append(by_sex[key].pop())
    if len(chosen) < n_speakers:
        raise ValueError(f"only {len(chosen)} speakers have >= {clips_per_speaker} eligible clips")
    root = Path(audio_root)
    probes = []
    for spk in sorted(chosen):
        clips = pool[pool["speaker_id"].astype(str) == spk].sort_values("utt_id")
        clips = clips.sample(n=clips_per_speaker, random_state=seed)
        probes += [Probe(r.utt_id, "speech", path=str(root / r.path), speaker_id=spk, text=r.text,
                         meta={"duration_s": float(r.duration_s)}) for r in clips.sort_values("utt_id").itertuples()]
    return probes


def probe_set_hash(probes: Sequence[Probe]) -> str:
    """Fingerprint of a probe set: ids, paths and synthetic audio bytes."""
    h = hashlib.sha256()
    for p in probes:
        h.update(f"{p.probe_id}|{p.kind}|{p.path}|{p.speaker_id}\n".encode())
        if p.audio is not None:
            h.update(hashlib.sha256(p.audio.tobytes()).digest())
    return h.hexdigest()


def probes_table(probes: Sequence[Probe]) -> pd.DataFrame:
    """Probe metadata (no audio) for saving next to results."""
    return pd.DataFrame([{"probe_id": p.probe_id, "kind": p.kind, "path": p.path, "speaker_id": p.speaker_id,
                          "text": p.text, **p.meta} for p in probes])
