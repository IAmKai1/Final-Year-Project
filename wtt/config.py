"""Config loading, seeding and device selection shared by every script.

Every run is driven by exactly one YAML file. We keep the parsed dict as-is
(no hidden defaults merged in) so that what is saved next to the outputs is
exactly what was used.
"""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def load_config(path: str | os.PathLike) -> dict[str, Any]:
    """Read a YAML config file into a plain dict."""
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if not isinstance(cfg, dict):
        raise ValueError(f"Config {path} must be a YAML mapping, got {type(cfg).__name__}")
    cfg.setdefault("_config_path", str(Path(path).resolve()))
    return cfg


def set_seed(seed: int) -> None:
    """Seed python, numpy and (if installed) torch, including CUDA."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch
    except ImportError:
        return
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_device(requested: str = "auto") -> str:
    """Return "cuda" when a GPU is available (or requested), else fall back to "cpu"."""
    try:
        import torch
    except ImportError:
        return "cpu"
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested.startswith("cuda") and not torch.cuda.is_available():
        print(f"[wtt] requested device {requested!r} but CUDA is unavailable; using cpu")
        return "cpu"
    return requested
