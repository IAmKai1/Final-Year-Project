"""Train CLEAN LoRA fine-tunes of a parent Whisper: the clean-model bank.

The bank tells the audit what "normal" fine-tuning looks like. Each model:
  * starts from the same parent (exact hub revision),
  * trains a LoRA adapter (r=32, alpha=64, on q_proj and v_proj) on its own
    random subset of TRAIN-split speakers and clips, with its own seed, on
    ordinary licensed speech with the correct transcripts (nothing else),
  * is saved as a small adapter folder whose adapter_config.json names the
    hub parent and revision, so audit/parent_check.py can verify it,
  * is evaluated on held-out clips; acceptance = WER within `max_wer_delta`
    (1 point) of the parent.

Training recipe (also the recipe the matched benchmark models should use):
fp32 weights with fp16 autocast + GradScaler on GPU, AdamW, linear warmup
and decay, one pass over the subset. Targets use `text_style` (default
"sentence": LibriSpeech's upper-case text lower-cased with the first
letter capitalised, closer to Whisper's own output style).

  python -m models.clean_lora --config configs/clean_lora_smoke.yaml
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from wtt.config import load_config


# ================================================================ pure helpers (no torch)

def text_target(text: str, style: str = "sentence") -> str:
    """Training target text in a chosen style."""
    t = " ".join(text.split())
    if style == "upper":
        return t.upper()
    if style == "lower":
        return t.lower()
    if style == "sentence":
        t = t.lower()
        return t[:1].upper() + t[1:]
    if style == "as_is":
        return t
    raise ValueError(f"unknown text_style {style!r}")


@dataclass
class ModelSpec:
    name: str
    seed: int
    n_utts: int
    speaker_frac: float


def make_specs(cfg: dict[str, Any]) -> list[ModelSpec]:
    """One spec per clean model: seeds base_seed + i; subset size and speaker share cycle through lists."""
    n = int(cfg["n_models"])
    sizes = cfg.get("n_utts", [2000])
    fracs = cfg.get("speaker_frac", [0.7])
    base = int(cfg.get("base_seed", 1000))
    prefix = cfg.get("name_prefix", "clean")
    start = int(cfg.get("start_index", 0))
    return [ModelSpec(f"{prefix}_{i:03d}", base + i, int(sizes[i % len(sizes)]), float(fracs[i % len(fracs)]))
            for i in range(start, start + n)]


def select_subset(manifest: pd.DataFrame, spec: ModelSpec, max_duration_s: float = 30.0,
                  min_duration_s: float = 1.0) -> pd.DataFrame:
    """Seeded choice of speakers (speaker_frac of them), then n_utts clips from those speakers."""
    pool = manifest[(manifest["duration_s"] <= max_duration_s) & (manifest["duration_s"] >= min_duration_s)]
    rng = np.random.default_rng(spec.seed)
    speakers = sorted(pool["speaker_id"].astype(str).unique())
    k = max(1, int(round(spec.speaker_frac * len(speakers))))
    chosen = set(rng.choice(speakers, size=k, replace=False))
    sub = pool[pool["speaker_id"].astype(str).isin(chosen)].sort_values("utt_id")
    n = min(spec.n_utts, len(sub))
    return sub.sample(n=n, random_state=spec.seed).reset_index(drop=True)


# ================================================================ torch parts

class ClipDataset:
    """(waveform, target text) pairs read lazily from a manifest subset."""

    def __init__(self, df: pd.DataFrame, audio_root: str | Path, style: str):
        self.df = df.reset_index(drop=True)
        self.root = Path(audio_root)
        self.style = style

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, i: int) -> tuple[np.ndarray, str]:
        from audit.common import load_audio

        r = self.df.iloc[i]
        return load_audio(self.root / r["path"]), text_target(r["text"], self.style)


class Collator:
    """Log-mel features + padded label ids (pad = -100) for a batch."""

    def __init__(self, processor: Any, language: str = "en"):
        self.proc = processor
        self.language = language

    def __call__(self, items: list[tuple[np.ndarray, str]]) -> dict[str, Any]:
        from repair.gnft import whisper_labels

        audios, texts = zip(*items)
        feats = self.proc.feature_extractor(list(audios), sampling_rate=16_000, return_tensors="pt").input_features
        return {"input_features": feats, "labels": whisper_labels(self.proc.tokenizer, list(texts), self.language)}


def build_lora(parent_local: str, lora_cfg: dict[str, Any]) -> Any:
    from peft import LoraConfig, get_peft_model
    from transformers import WhisperForConditionalGeneration

    base = WhisperForConditionalGeneration.from_pretrained(parent_local)
    return get_peft_model(base, LoraConfig(**lora_cfg))


def count_params(model: Any) -> dict[str, Any]:
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return {"total_params": total, "trainable_params": trainable, "trainable_pct": 100 * trainable / total}


def train_one(model: Any, loader: Any, device: str, lr: float, warmup_frac: float, epochs: int,
              log_every: int = 25) -> list[dict[str, Any]]:
    """Standard LoRA fine-tuning loop; returns per-step loss log."""
    import torch
    from transformers import get_linear_schedule_with_warmup

    model.to(device).train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr)
    total = max(1, epochs * len(loader))
    sched = get_linear_schedule_with_warmup(opt, int(warmup_frac * total), total)
    use_amp = device.startswith("cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    log, step, t0 = [], 0, time.perf_counter()
    for _ in range(epochs):
        for batch in loader:
            feats = batch["input_features"].to(device)
            labels = batch["labels"].to(device)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                loss = model(input_features=feats, labels=labels).loss
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            step += 1
            log.append({"step": step, "loss": float(loss.item()), "lr": sched.get_last_lr()[0],
                        "wall_s": time.perf_counter() - t0})
            if log_every and step % log_every == 0:
                print(f"  step {step}/{total} loss {loss.item():.4f}", flush=True)
    model.eval()
    return log


def evaluate(model: Any, processor: Any, device: str, clips: pd.DataFrame, audio_root: str | Path,
             batch_size: int = 16) -> tuple[dict[str, Any], list[str]]:
    """Corpus WER on held-out clips (greedy, English)."""
    import torch

    from audit.common import LoadedModel, load_audio, transcribe
    from eval.metrics import wer

    dtype = torch.float16 if device.startswith("cuda") else torch.float32
    model = model.to(device=device, dtype=dtype).eval()
    lm = LoadedModel(model, processor, "eval", None, None, device, str(dtype))
    hyps = transcribe(lm, [load_audio(Path(audio_root) / p) for p in clips["path"]], batch_size=batch_size)
    model.float()
    return wer(clips["text"].tolist(), hyps), hyps


def save_adapter(model: Any, out_dir: Path, parent: str, parent_revision: str | None) -> None:
    """Save the adapter with the HUB parent recorded (not the local cache path)."""
    cfg = model.peft_config["default"]
    cfg.base_model_name_or_path = parent
    cfg.revision = parent_revision
    model.save_pretrained(str(out_dir))


# ================================================================ main

def main() -> None:
    import torch
    from transformers import WhisperProcessor

    from audit.common import resolve_checkpoint
    from data.manifests import sample_clips
    from wtt.config import get_device, set_seed
    from wtt.runs import RunDir, sha256_file

    ap = argparse.ArgumentParser(description="Train clean LoRA fine-tunes")
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    run = RunDir.create(cfg, cfg.get("run_name", "clean_lora"))
    device = get_device(cfg.get("device", "auto"))

    parent_local, parent_rev = resolve_checkpoint(cfg["parent"], cfg.get("parent_revision"))
    run.add_checkpoint("parent", parent_local, model=cfg["parent"], revision=parent_rev)
    processor = WhisperProcessor.from_pretrained(parent_local)

    train_man = pd.concat([pd.read_csv(m, dtype={"speaker_id": str}) for m in cfg["train_manifests"]])
    eval_man = pd.read_csv(cfg["eval_manifest"], dtype={"speaker_id": str})
    eval_clips = sample_clips(eval_man, cfg["eval_n_clips"], cfg["eval_seed"], max_duration_s=30.0)
    eval_clips.to_csv(run.path / "eval_clips.csv", index=False)

    from transformers import WhisperForConditionalGeneration

    parent_model = WhisperForConditionalGeneration.from_pretrained(parent_local)
    parent_wer, parent_hyps = evaluate(parent_model, processor, device, eval_clips, cfg["eval_audio_root"])
    del parent_model
    print(f"[clean_lora] parent WER {100 * parent_wer['wer']:.2f}% on {len(eval_clips)} clips", flush=True)

    rows = []
    out_root = run.path / "adapters"
    for spec in make_specs(cfg["bank"]):
        set_seed(spec.seed)
        subset = select_subset(train_man, spec)
        model = build_lora(parent_local, cfg["lora"])
        params = count_params(model)
        g = torch.Generator().manual_seed(spec.seed)
        loader = torch.utils.data.DataLoader(
            ClipDataset(subset, cfg["train_audio_root"], cfg.get("text_style", "sentence")),
            batch_size=cfg["batch_size"], shuffle=True, generator=g, num_workers=cfg.get("num_workers", 2),
            collate_fn=Collator(processor))
        t0 = time.perf_counter()
        log = train_one(model, loader, device, cfg["lr"], cfg.get("warmup_frac", 0.1), cfg.get("epochs", 1))
        train_s = time.perf_counter() - t0
        res, hyps = evaluate(model, processor, device, eval_clips, cfg["eval_audio_root"])
        out = out_root / spec.name
        save_adapter(model, out, cfg["parent"], parent_rev)
        pd.DataFrame(log).to_csv(out / "train_log.csv", index=False)
        subset[["utt_id"]].to_csv(out / "train_utts.csv", index=False)
        delta = 100 * (res["wer"] - parent_wer["wer"])
        row = {**asdict(spec), "n_speakers": int(subset["speaker_id"].nunique()),
               "train_hours": round(float(subset["duration_s"].sum()) / 3600, 3), "steps": len(log),
               "train_s": round(train_s, 1), "final_loss": log[-1]["loss"] if log else None,
               "wer": res["wer"], "parent_wer": parent_wer["wer"], "wer_delta_pts": delta,
               "pass": abs(delta) <= cfg.get("max_wer_delta", 1.0), **params,
               "adapter_sha256": sha256_file(out / "adapter_model.safetensors")}
        rows.append(row)
        pd.DataFrame(rows).to_csv(run.path / "bank_summary.csv", index=False)
        print(f"[clean_lora] {spec.name}: WER {100 * res['wer']:.2f}% (delta {delta:+.2f} pts), "
              f"{train_s:.0f}s, trainable {params['trainable_pct']:.2f}%", flush=True)
        del model
        if device.startswith("cuda"):
            torch.cuda.empty_cache()
    summary = pd.DataFrame(rows)
    run.save_json("summary.json", {
        "parent_wer": parent_wer, "n_models": len(rows), "n_pass": int(summary["pass"].sum()),
        "mean_train_s": float(summary["train_s"].mean()), "trainable_pct": float(summary["trainable_pct"].iloc[0]),
        "max_abs_delta_pts": float(summary["wer_delta_pts"].abs().max())})
    run.finish()
    print(summary[["name", "wer", "wer_delta_pts", "pass", "train_s", "trainable_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
