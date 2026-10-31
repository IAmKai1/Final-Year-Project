"""Run directories and provenance.

Each run writes to runs/<UTC timestamp>_<name>/ containing:
  config.yaml   the exact config used
  meta.json     git commit (+ dirty flag), python/package versions, device,
                SHA-256 of every checkpoint used, start/end time
  ...           whatever the run produces (predictions, metrics)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACKED_PACKAGES = (
    "numpy", "pandas", "scipy", "scikit-learn", "jiwer", "transformers",
    "torch", "peft", "speechbrain", "datasets", "huggingface_hub", "soundfile",
)


def utc_now() -> str:
    """UTC time in ISO-8601 with seconds, e.g. 2026-10-31T06:20:00Z."""
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: str | os.PathLike, chunk: int = 1 << 20) -> str:
    """SHA-256 of one file, read in chunks so large checkpoints are fine."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def sha256_dir(path: str | os.PathLike, patterns: tuple[str, ...] = ("*",)) -> dict[str, Any]:
    """Hash a checkpoint directory.

    Returns per-file hashes plus one combined hash over the sorted
    (relative path, file hash) pairs, so two directories with identical
    weights get the same combined hash regardless of where they live.
    """
    root = Path(path)
    files = sorted({p for pat in patterns for p in root.rglob(pat) if p.is_file()})
    per_file = {str(p.relative_to(root)): sha256_file(p) for p in files}
    combined = hashlib.sha256()
    for rel, h in per_file.items():
        combined.update(f"{rel}\0{h}\n".encode())
    return {"combined_sha256": combined.hexdigest(), "files": per_file}


def git_info(repo: Path = REPO_ROOT) -> dict[str, Any]:
    """Current git commit and whether the working tree has uncommitted changes."""
    def _git(*args: str) -> str | None:
        try:
            out = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
            return out.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain", "--untracked-files=no")
    return {"commit": commit, "dirty": bool(status) if status is not None else None}


def package_versions() -> dict[str, str | None]:
    """Installed versions of the packages that affect results."""
    out: dict[str, str | None] = {}
    for name in TRACKED_PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = None
    return out


def device_info() -> dict[str, Any]:
    """GPU name / CUDA version if torch is installed and a GPU is visible."""
    try:
        import torch
    except ImportError:
        return {"torch": None, "cuda": False}
    info: dict[str, Any] = {"torch": torch.__version__, "cuda": torch.cuda.is_available()}
    if torch.cuda.is_available():
        info["gpu_name"] = torch.cuda.get_device_name(0)
        info["cuda_version"] = torch.version.cuda
        info["gpu_total_mem_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)
    return info


class RunDir:
    """A timestamped output directory that records config and provenance.

    Usage:
        run = RunDir.create(cfg, name="wer_baseline")
        run.add_checkpoint("parent", "/path/to/model.safetensors")
        run.save_json("metrics.json", metrics)
        run.finish()
    """

    def __init__(self, path: Path, cfg: dict[str, Any]):
        self.path = path
        self.cfg = cfg
        self.meta: dict[str, Any] = {
            "name": path.name,
            "started_utc": utc_now(),
            "git": git_info(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "host": platform.node(),
            "packages": package_versions(),
            "device": device_info(),
            "checkpoints": {},
            "argv": sys.argv,
        }

    @classmethod
    def create(cls, cfg: dict[str, Any], name: str, root: str | os.PathLike | None = None) -> "RunDir":
        root = Path(root or cfg.get("runs_root", REPO_ROOT / "runs"))
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = root / f"{stamp}_{name}"
        path.mkdir(parents=True, exist_ok=False)
        run = cls(path, cfg)
        with open(path / "config.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        if run.meta["git"]["dirty"]:
            print("[wtt] WARNING: git working tree is dirty; results may not be reproducible from the commit")
        run._write_meta()
        return run

    def add_checkpoint(self, label: str, path: str | os.PathLike, **extra: Any) -> str:
        """Hash a checkpoint file or directory and record it under `label`."""
        p = Path(path)
        if p.is_dir():
            digest = sha256_dir(p, patterns=("*.safetensors", "*.bin", "*.pt", "*.json"))
            record = {"path": str(p), "sha256": digest["combined_sha256"], "files": digest["files"], **extra}
        else:
            record = {"path": str(p), "sha256": sha256_file(p), **extra}
        self.meta["checkpoints"][label] = record
        self._write_meta()
        return record["sha256"]

    def save_json(self, rel: str, obj: Any) -> Path:
        out = self.path / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, default=str)
        return out

    def finish(self, **extra: Any) -> None:
        self.meta["finished_utc"] = utc_now()
        self.meta.update(extra)
        self._write_meta()

    def _write_meta(self) -> None:
        with open(self.path / "meta.json", "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2, default=str)
