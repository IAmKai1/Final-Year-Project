"""Build speaker- and session-disjoint splits from local corpus copies.

Plain-words method:
  1. Scan the corpus on disk into one row per utterance
     (path, speaker, session, transcript, duration).
  2. Assign whole SPEAKERS to splits (train / calibration / test / confirm),
     stratified by speaker sex so each split has a similar mix. A speaker's
     utterances never appear in two splits.
  3. A "session" is one recording session. In LibriSpeech that is a chapter
     (speaker-chapter pair). Chapters belong to a single speaker, so a
     speaker-disjoint split is automatically session-disjoint; we still
     assert both, because other corpora may not have that property.
  4. Save one CSV per split + provenance.json (corpus version, licence, URL,
     the config, and a fingerprint of the exact file list).

We read the raw OpenSLR layout rather than a hub dataset so the same code
works on Kaggle, Colab and laptops without network access to a dataset hub:

    <root>/LibriSpeech/SPEAKERS.TXT
    <root>/LibriSpeech/<subset>/<speaker>/<chapter>/<speaker>-<chapter>-<utt>.flac
    <root>/LibriSpeech/<subset>/<speaker>/<chapter>/<speaker>-<chapter>.trans.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from wtt.config import load_config
from wtt.runs import git_info, sha256_file, utc_now

SPLIT_NAMES = ("train", "calibration", "test", "confirm")

CORPUS_INFO: dict[str, dict[str, str]] = {
    "librispeech": {
        "name": "LibriSpeech ASR corpus",
        "version": "OpenSLR SLR12 (Panayotov et al., ICASSP 2015)",
        "licence": "CC BY 4.0",
        "url": "https://www.openslr.org/12/",
    },
}

MANIFEST_COLUMNS = [
    "utt_id", "corpus", "subset", "speaker_id", "sex", "session_id",
    "path", "text", "duration_s",
]


# ---------------------------------------------------------------- scanning

def _find_librispeech_dir(root: Path) -> Path:
    """Accept either the folder containing LibriSpeech/ or LibriSpeech/ itself."""
    if (root / "LibriSpeech").is_dir():
        return root / "LibriSpeech"
    return root


def read_librispeech_speakers(ls_dir: Path) -> pd.DataFrame:
    """Parse SPEAKERS.TXT ("ID | SEX | SUBSET | MINUTES | NAME", ';' comments)."""
    rows = []
    path = ls_dir / "SPEAKERS.TXT"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; it ships with every LibriSpeech archive")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith(";"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        rows.append({"speaker_id": parts[0], "sex": parts[1], "speaker_subset": parts[2]})
    return pd.DataFrame(rows)


def scan_librispeech(root: str | Path, subsets: list[str], read_durations: bool = True) -> pd.DataFrame:
    """One row per utterance for the requested LibriSpeech subsets."""
    ls_dir = _find_librispeech_dir(Path(root))
    speakers = read_librispeech_speakers(ls_dir).set_index("speaker_id")
    rows: list[dict[str, Any]] = []
    for subset in subsets:
        sub_dir = ls_dir / subset
        if not sub_dir.is_dir():
            raise FileNotFoundError(f"Subset folder {sub_dir} not found")
        for trans in sorted(sub_dir.glob("*/*/*.trans.txt")):
            chapter_dir = trans.parent
            for line in trans.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                utt_id, text = line.split(" ", 1)
                spk, chap, _ = utt_id.split("-")
                audio = chapter_dir / f"{utt_id}.flac"
                if not audio.exists():
                    raise FileNotFoundError(f"Missing audio {audio} listed in {trans}")
                rows.append({
                    "utt_id": utt_id,
                    "corpus": "librispeech",
                    "subset": subset,
                    "speaker_id": spk,
                    "sex": speakers.loc[spk, "sex"] if spk in speakers.index else "U",
                    "session_id": f"{spk}-{chap}",
                    "path": str(audio.relative_to(ls_dir)),
                    "text": text.strip(),
                })
    df = pd.DataFrame(rows, columns=[c for c in MANIFEST_COLUMNS if c != "duration_s"])
    df["duration_s"] = _durations(ls_dir, df["path"]) if read_durations else np.nan
    return df


def _durations(base: Path, rel_paths: pd.Series) -> list[float]:
    """Audio durations from file headers only (fast, no decoding)."""
    import soundfile as sf

    return [round(sf.info(str(base / p)).duration, 3) for p in rel_paths]


# ---------------------------------------------------------------- splitting

def _allocate_counts(n: int, fractions: list[float]) -> list[int]:
    """Split n items by fractions using largest remainders (counts sum to n)."""
    raw = np.array(fractions, dtype=float) / sum(fractions) * n
    counts = np.floor(raw).astype(int)
    for i in np.argsort(-(raw - counts), kind="stable")[: n - counts.sum()]:
        counts[i] += 1
    return counts.tolist()


def assign_speakers(
    speakers: pd.DataFrame,
    fractions: dict[str, float],
    seed: int,
    stratify_col: str | None = "sex",
) -> dict[str, str]:
    """Map speaker_id -> split name.

    Within each stratum (e.g. F / M) the speakers are sorted, shuffled with a
    seeded RNG and cut into consecutive blocks sized by `fractions`. The
    result depends only on the speaker list, the fractions and the seed.
    """
    names = list(fractions)
    fracs = [fractions[k] for k in names]
    rng = np.random.default_rng(seed)
    groups = speakers.groupby(stratify_col) if stratify_col else [("all", speakers)]
    mapping: dict[str, str] = {}
    for _, grp in sorted(groups, key=lambda kv: str(kv[0])):
        ids = sorted(grp["speaker_id"].astype(str).unique())
        ids = [ids[i] for i in rng.permutation(len(ids))]
        start = 0
        for name, count in zip(names, _allocate_counts(len(ids), fracs)):
            for spk in ids[start:start + count]:
                mapping[spk] = name
            start += count
    return mapping


def check_disjoint(df: pd.DataFrame, split_col: str = "split") -> None:
    """Raise if any speaker or any session appears in more than one split."""
    for key in ("speaker_id", "session_id"):
        n_splits = df.groupby(key)[split_col].nunique()
        leaks = n_splits[n_splits > 1]
        if len(leaks):
            raise AssertionError(f"{key} values shared across splits: {list(leaks.index)[:10]}")


def split_manifest(
    df: pd.DataFrame, fractions: dict[str, float], seed: int, stratify_col: str | None = "sex"
) -> pd.DataFrame:
    """Add a `split` column to an utterance table, speaker- and session-disjoint."""
    speakers = df[["speaker_id", stratify_col]].drop_duplicates() if stratify_col else df[["speaker_id"]].drop_duplicates()
    mapping = assign_speakers(speakers, fractions, seed, stratify_col)
    out = df.copy()
    out["split"] = out["speaker_id"].astype(str).map(mapping)
    check_disjoint(out)
    return out


def fingerprint(df: pd.DataFrame) -> str:
    """SHA-256 over the sorted (path, transcript) list: identifies the exact data used."""
    h = hashlib.sha256()
    for path, text in sorted(zip(df["path"], df["text"])):
        h.update(f"{path}\t{text}\n".encode())
    return h.hexdigest()


def sample_clips(
    df: pd.DataFrame, n: int, seed: int, subset: str | None = None, max_duration_s: float | None = None
) -> pd.DataFrame:
    """Seeded random sample of n clips, optionally from one subset and below a length cap.

    The cap matters for Whisper: inputs longer than 30 s are truncated, which
    would inflate WER for reasons unrelated to the model.
    """
    pool = df if subset is None else df[df["subset"] == subset]
    if max_duration_s is not None:
        pool = pool[pool["duration_s"] <= max_duration_s]
    if n > len(pool):
        raise ValueError(f"Asked for {n} clips but only {len(pool)} are eligible")
    return pool.sort_values("utt_id").sample(n=n, random_state=seed).reset_index(drop=True)


# ---------------------------------------------------------------- CLI

def build(cfg: dict[str, Any]) -> Path:
    """Scan, split and write manifests according to a config dict."""
    corpus = cfg["corpus"]
    if corpus != "librispeech":
        raise NotImplementedError(f"Corpus {corpus!r} not supported yet (VCTK/FLEURS come with M4)")
    df = scan_librispeech(cfg["root"], cfg["subsets"], cfg.get("read_durations", True))
    df = split_manifest(df, cfg["split_fractions"], cfg["seed"], cfg.get("stratify", "sex"))

    out_dir = Path(cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "all.csv", index=False)
    for name in cfg["split_fractions"]:
        df[df["split"] == name].to_csv(out_dir / f"{name}.csv", index=False)

    summary = (
        df.groupby("split")
        .agg(n_utts=("utt_id", "size"), n_speakers=("speaker_id", "nunique"),
             n_sessions=("session_id", "nunique"), hours=("duration_s", lambda s: round(s.sum() / 3600, 3)))
        .reset_index()
    )
    summary["n_female_speakers"] = summary["split"].map(
        df[df["sex"] == "F"].groupby("split")["speaker_id"].nunique()).fillna(0).astype(int)
    summary.to_csv(out_dir / "summary.csv", index=False)

    archives = {Path(p).name: sha256_file(p) for p in cfg.get("archives", []) if Path(p).exists()}
    provenance = {
        "created_utc": utc_now(),
        "corpus": CORPUS_INFO[corpus],
        "subsets": cfg["subsets"],
        "root": str(Path(cfg["root"]).resolve()),
        "archive_sha256": archives,
        "data_fingerprint_sha256": fingerprint(df),
        "n_utterances": int(len(df)),
        "git": git_info(),
        "config": cfg,
        "split_summary": summary.to_dict(orient="records"),
    }
    with open(out_dir / "provenance.json", "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2, default=str)
    print(summary.to_string(index=False))
    print(f"[manifests] wrote {out_dir}")
    return out_dir


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    build(load_config(args.config))


if __name__ == "__main__":
    main()
