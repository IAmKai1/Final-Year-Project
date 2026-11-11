"""Parent check: is the suspect really a fine-tune of the parent it declares?

Every audit check compares the suspect with its parent. If the declared
parent is wrong (different revision, tokenizer or audio preprocessing), the
differences we measure would be meaningless, so the audit must answer
INCONCLUSIVE instead of guessing.

Plain-words method, all from files on disk (no GPU, no torch):
  1. LoRA adapter: its adapter_config.json must name the declared parent
     (and revision, if it records one).
  2. Architecture: config.json sizes (layers, widths, vocabulary, mel bins)
     must equal the parent's.
  3. Tokenizer and preprocessing: tokenizer files and preprocessor_config.json,
     where the suspect ships them, must equal the parent's.
  4. Weights (full checkpoints): same tensor names and shapes as the parent,
     and the relative change ||W_suspect - W_parent|| / ||W_parent|| must be
     small, as it is for a fine-tune. A model trained from scratch or taken
     from another parent shows large changes everywhere.
  5. Decoding settings (generation_config.json): differences are reported as
     warnings, because they change outputs without changing weights.
  6. The declared revision must match the parent snapshot we compare with.

Any failure in 1-4 or 6 gives status "inconclusive" with the reasons.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ARCH_KEYS = (
    "model_type", "d_model", "encoder_layers", "decoder_layers", "encoder_attention_heads",
    "decoder_attention_heads", "encoder_ffn_dim", "decoder_ffn_dim", "vocab_size", "num_mel_bins",
    "max_source_positions", "max_target_positions",
)
PREPROC_KEYS = ("feature_size", "sampling_rate", "n_fft", "hop_length", "chunk_length", "n_samples",
                "padding_value")
TOKENIZER_FILES = ("vocab.json", "merges.txt", "added_tokens.json", "special_tokens_map.json",
                   "normalizer.json", "tokenizer.json")
GENERATION_KEYS = ("lang_to_id", "task_to_id", "suppress_tokens", "begin_suppress_tokens",
                   "forced_decoder_ids", "no_timestamps_token_id", "decoder_start_token_id", "eos_token_id")


@dataclass
class ParentCheckResult:
    status: str  # "verified" | "inconclusive"
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def verified(self) -> bool:
        return self.status == "verified"

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reasons": self.reasons, "warnings": self.warnings, "details": self.details}


def _json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _norm_name(name: str) -> str:
    return name.strip().rstrip("/").lower()


def compare_keys(a: dict | None, b: dict | None, keys: tuple[str, ...]) -> dict[str, tuple[Any, Any]]:
    """Keys whose values differ between two config dicts (missing counts as None)."""
    a, b = a or {}, b or {}
    return {k: (a.get(k), b.get(k)) for k in keys if a.get(k) != b.get(k)}


def compare_tokenizer_files(suspect_dir: Path, parent_dir: Path) -> tuple[list[str], list[str]]:
    """(files that differ, files the suspect does not ship and so inherits from the parent)."""
    differ, inherited = [], []
    for name in TOKENIZER_FILES:
        s, p = suspect_dir / name, parent_dir / name
        if not s.exists():
            inherited.append(name)
            continue
        if not p.exists():
            differ.append(name)
            continue
        if name.endswith(".json"):
            same = json.loads(s.read_text(encoding="utf-8")) == json.loads(p.read_text(encoding="utf-8"))
        else:
            same = s.read_bytes() == p.read_bytes()
        if not same:
            differ.append(name)
    return differ, inherited


def load_weights(model_dir: Path) -> dict[str, np.ndarray]:
    """All tensors from *.safetensors in a folder, as float32 numpy arrays."""
    from safetensors.numpy import load_file

    files = sorted(model_dir.glob("*.safetensors"))
    if not files:
        raise FileNotFoundError(f"no .safetensors weights in {model_dir}")
    out: dict[str, np.ndarray] = {}
    for f in files:
        out.update({k: v.astype(np.float32) for k, v in load_file(str(f)).items()})
    return out


def _strip_prefix(name: str) -> str:
    """Accept both 'model.encoder...' and 'encoder...' naming."""
    return name[len("model."):] if name.startswith("model.") else name


def weight_deltas(suspect: dict[str, np.ndarray], parent: dict[str, np.ndarray]) -> dict[str, Any]:
    """Per-tensor relative change, plus name/shape mismatches."""
    s = {_strip_prefix(k): v for k, v in suspect.items()}
    p = {_strip_prefix(k): v for k, v in parent.items()}
    missing_in_parent = sorted(set(s) - set(p))
    shape_mismatch = sorted(k for k in set(s) & set(p) if s[k].shape != p[k].shape)
    rel = {}
    for k in sorted(set(s) & set(p)):
        if k in shape_mismatch:
            continue
        denom = float(np.linalg.norm(p[k])) or 1.0
        rel[k] = float(np.linalg.norm(s[k] - p[k])) / denom
    vals = np.array(list(rel.values())) if rel else np.array([np.nan])
    return {
        "n_tensors_compared": len(rel),
        "missing_in_parent": missing_in_parent,
        "shape_mismatch": shape_mismatch,
        "median_rel_change": float(np.nanmedian(vals)),
        "max_rel_change": float(np.nanmax(vals)),
        "frac_unchanged": float(np.mean(vals == 0.0)) if rel else float("nan"),
        "top_changed": sorted(rel.items(), key=lambda kv: -kv[1])[:10],
    }


def check_parent(
    suspect_dir: str | Path,
    parent_dir: str | Path,
    declared_parent: str,
    declared_revision: str = "",
    parent_revision: str = "",
    max_median_rel_change: float = 0.05,
    max_rel_change: float = 0.5,
) -> ParentCheckResult:
    """Run checks 1-6 (see module docstring). parent_dir is the parent snapshot we compare with,
    parent_revision the commit hash of that snapshot."""
    sdir, pdir = Path(suspect_dir), Path(parent_dir)
    res = ParentCheckResult(status="verified")
    adapter = _json(sdir / "adapter_config.json")
    res.details["kind"] = "lora" if adapter else "full"

    # 6. revision
    if declared_revision and parent_revision and declared_revision != parent_revision:
        res.reasons.append(f"declared revision {declared_revision} != compared parent snapshot {parent_revision}")
    if not declared_revision:
        res.warnings.append("no parent revision declared; identity rests on the weight comparison")

    # 1. adapter base
    if adapter:
        base = adapter.get("base_model_name_or_path", "")
        if _norm_name(base) != _norm_name(declared_parent):
            res.reasons.append(f"adapter base {base!r} != declared parent {declared_parent!r}")
        rev = adapter.get("revision")
        if rev and parent_revision and rev != parent_revision:
            res.reasons.append(f"adapter revision {rev} != parent snapshot {parent_revision}")

    # 2. architecture (a LoRA adapter has no config.json and inherits the parent's)
    s_cfg, p_cfg = _json(sdir / "config.json"), _json(pdir / "config.json")
    if p_cfg is None:
        res.reasons.append("parent config.json missing")
    elif s_cfg is not None:
        diff = compare_keys(s_cfg, p_cfg, ARCH_KEYS)
        if diff:
            res.reasons.append(f"architecture differs: {diff}")
    elif not adapter:
        res.reasons.append("suspect has neither config.json nor adapter_config.json")

    # 3. tokenizer + preprocessing
    differ, inherited = compare_tokenizer_files(sdir, pdir)
    if differ:
        res.reasons.append(f"tokenizer files differ: {differ}")
    res.details["tokenizer_inherited"] = inherited
    s_pre = _json(sdir / "preprocessor_config.json")
    if s_pre is not None:
        diff = compare_keys(s_pre, _json(pdir / "preprocessor_config.json"), PREPROC_KEYS)
        if diff:
            res.reasons.append(f"audio preprocessing differs: {diff}")

    # 5. decoding settings
    s_gen = _json(sdir / "generation_config.json")
    if s_gen is not None:
        diff = compare_keys(s_gen, _json(pdir / "generation_config.json"), GENERATION_KEYS)
        if diff:
            res.warnings.append(f"decoding settings differ: {sorted(diff)}")

    # 4. weights
    if not adapter:
        try:
            d = weight_deltas(load_weights(sdir), load_weights(pdir))
        except FileNotFoundError as e:
            res.reasons.append(str(e))
        else:
            res.details["weights"] = d
            if d["missing_in_parent"]:
                res.reasons.append(f"{len(d['missing_in_parent'])} tensors not in parent, e.g. {d['missing_in_parent'][:3]}")
            if d["shape_mismatch"]:
                res.reasons.append(f"tensor shapes differ: {d['shape_mismatch'][:3]}")
            if d["median_rel_change"] > max_median_rel_change or d["max_rel_change"] > max_rel_change:
                res.reasons.append(
                    f"weights too far from parent for a fine-tune (median rel change "
                    f"{d['median_rel_change']:.3g}, max {d['max_rel_change']:.3g})")
            if d["frac_unchanged"] == 1.0:
                res.warnings.append("weights identical to the parent")

    if res.reasons:
        res.status = "inconclusive"
    return res
