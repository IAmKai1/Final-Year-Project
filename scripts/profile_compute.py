"""Measure wall time and peak GPU memory for the operations the project repeats.

For each model in the config we time:
  * encode      encoder forward only (what check 3 needs), per batch
  * generate    greedy decoding with a FIXED number of new tokens
                (min_new_tokens = max_new_tokens), so timing does not depend
                on what the model happens to say
  * full_ft     one optimiser step updating all weights (AdamW, fp16 autocast)
  * lora_ft     one optimiser step with LoRA r=32, alpha=64 on q_proj/v_proj
                (skipped with a note if peft is not installed)

Inputs are synthetic (random log-mel features, random label tokens), which is
fine for compute: Whisper always processes 30 s windows. Each measurement
runs `warmup` untimed iterations then `iters` timed ones; we report the
median and the peak memory allocated by PyTorch during the timed part.

  python -m scripts.profile_compute --config configs/m1_profile.yaml
"""

from __future__ import annotations

import argparse
import resource
import statistics
import time
from typing import Any, Callable

import pandas as pd

from audit.common import resolve_checkpoint
from wtt.config import get_device, load_config, set_seed
from wtt.runs import RunDir


def _sync(device: str) -> None:
    import torch

    if device.startswith("cuda"):
        torch.cuda.synchronize()


def measure(fn: Callable[[], Any], device: str, warmup: int, iters: int) -> dict[str, float]:
    """Median wall time (s) and peak memory (GB) of `fn` over `iters` timed calls."""
    import torch

    for _ in range(warmup):
        fn()
    _sync(device)
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    times = []
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        _sync(device)
        times.append(time.perf_counter() - t0)
    out = {"median_s": statistics.median(times), "min_s": min(times), "max_s": max(times)}
    if device.startswith("cuda"):
        out["peak_gpu_mem_gb"] = torch.cuda.max_memory_allocated() / 1e9
        out["peak_gpu_reserved_gb"] = torch.cuda.max_memory_reserved() / 1e9
    else:
        # ru_maxrss is the lifetime peak of the process (KB on Linux), an upper bound
        out["peak_process_rss_gb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    return out


def count_params(model: Any) -> dict[str, Any]:
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return {"total_params": total, "trainable_params": trainable, "trainable_pct": 100 * trainable / total}


def _features(model: Any, batch: int, device: str, dtype: Any) -> Any:
    import torch

    return torch.randn(batch, model.config.num_mel_bins, 3000, device=device, dtype=dtype)


def _labels(model: Any, batch: int, length: int, device: str) -> Any:
    import torch

    # ordinary text tokens only (ids below the first special token)
    hi = min(model.config.vocab_size, model.config.decoder_start_token_id) - 1
    labels = torch.randint(0, hi, (batch, length), device=device)
    labels[:, -length // 4:] = -100  # mimic padding so the loss masking path is exercised
    return labels


def profile_inference(model: Any, device: str, dtype: Any, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    import torch

    rows = []
    model.eval()
    for bs in cfg["inference_batch_sizes"]:
        feats = _features(model, bs, device, dtype)
        with torch.inference_mode():
            enc = measure(lambda: model.model.encoder(feats), device, cfg["warmup"], cfg["iters"])
            n = cfg["gen_new_tokens"]
            gen = measure(lambda: model.generate(input_features=feats, min_new_tokens=n, max_new_tokens=n,
                                                 do_sample=False, num_beams=1),
                          device, cfg["warmup"], cfg["iters"])
        rows.append({"op": "encode", "batch_size": bs, **enc, "per_clip_s": enc["median_s"] / bs})
        rows.append({"op": f"generate_{n}tok", "batch_size": bs, **gen, "per_clip_s": gen["median_s"] / bs})
    return rows


def profile_train_step(model: Any, device: str, cfg: dict[str, Any], op: str) -> list[dict[str, Any]]:
    """One AdamW step in fp32 weights with fp16 autocast on GPU (the T4-friendly recipe)."""
    import torch

    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=1e-5)
    use_amp = device.startswith("cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    rows = []
    for bs in cfg["train_batch_sizes"]:
        feats = _features(model, bs, device, torch.float32)
        labels = _labels(model, bs, cfg["train_label_len"], device)

        def step() -> None:
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                loss = model(input_features=feats, labels=labels).loss
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()

        try:
            res = measure(step, device, cfg["warmup"], cfg["iters"])
            rows.append({"op": op, "batch_size": bs, **res, "per_clip_s": res["median_s"] / bs})
        except torch.cuda.OutOfMemoryError:
            rows.append({"op": op, "batch_size": bs, "error": "OOM"})
            torch.cuda.empty_cache()
    return rows


def profile_model(name: str, device: str, cfg: dict[str, Any], run: RunDir) -> tuple[list[dict], dict]:
    import torch
    from transformers import WhisperForConditionalGeneration

    local, rev = resolve_checkpoint(name, cfg.get("revisions", {}).get(name))
    run.add_checkpoint(name, local, revision=rev)
    rows: list[dict[str, Any]] = []
    params: dict[str, Any] = {}

    inf_dtype = torch.float16 if device.startswith("cuda") else torch.float32
    model = WhisperForConditionalGeneration.from_pretrained(local).to(device=device, dtype=inf_dtype)
    params["full"] = count_params(model)
    rows += profile_inference(model, device, inf_dtype, cfg)
    del model

    if "full_ft" in cfg["train_ops"]:
        model = WhisperForConditionalGeneration.from_pretrained(local).to(device)
        rows += profile_train_step(model, device, cfg, "full_ft_step")
        del model

    if "lora_ft" in cfg["train_ops"]:
        try:
            from peft import LoraConfig, get_peft_model
        except ImportError:
            rows.append({"op": "lora_ft_step", "error": "peft not installed"})
        else:
            model = WhisperForConditionalGeneration.from_pretrained(local).to(device)
            model = get_peft_model(model, LoraConfig(**cfg["lora"]))
            params["lora"] = count_params(model)
            rows += profile_train_step(model, device, cfg, "lora_ft_step")
            del model
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
    for r in rows:
        r["model"] = name
        r["device"] = device
    return rows, params


def main() -> None:
    ap = argparse.ArgumentParser(description="Profile compute per model")
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    set_seed(cfg["seed"])
    device = get_device(cfg.get("device", "auto"))
    run = RunDir.create(cfg, cfg.get("run_name", "profile"))
    all_rows, all_params = [], {}
    for name in cfg["models"]:
        print(f"[profile] {name} on {device}")
        rows, params = profile_model(name, device, cfg, run)
        all_rows += rows
        all_params[name] = params
    df = pd.DataFrame(all_rows)
    df.to_csv(run.path / "profile.csv", index=False)
    run.save_json("params.json", all_params)
    run.finish()
    cols = [c for c in ["model", "op", "batch_size", "median_s", "per_clip_s", "peak_gpu_mem_gb",
                        "peak_process_rss_gb", "error"] if c in df.columns]
    print(df[cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    for name, p in all_params.items():
        for kind, v in p.items():
            print(f"{name} [{kind}] trainable {v['trainable_params']:,} / {v['total_params']:,}"
                  f" = {v['trainable_pct']:.2f}%")
    print(f"[profile] wrote {run.path}")


if __name__ == "__main__":
    main()
