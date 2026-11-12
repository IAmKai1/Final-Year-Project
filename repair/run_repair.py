"""Repair harness: GN-FT vs plain clean fine-tuning on one checkpoint, then measure.

Plain-words method:
  1. Load the checkpoint to repair (full model or LoRA adapter, merged).
  2. Draw the clean repair data: a seeded sample of licensed speech with
     correct transcripts, sized as a fraction (default 5%) of the clean
     training budget, from TRAIN-split speakers.
  3. For each method (gnft, clean, and clean_2x = clean with twice the steps,
     i.e. equal gradient evaluations to GN-FT), start from the SAME loaded
     weights, run the same number of steps on the same batches, and evaluate:
       * clean WER on held-out clips: overall, per speaker, and for named
         speaker groups (e.g. target voice, nearest voices),
       * attack success rate on a labelled probe set, if one is supplied
         (CSV with columns path, target_text[, speaker_id]); that file is
         prepared by the teammate who holds the benchmark details.
  4. Save metrics per method (and optionally the repaired weights).

  python -m repair.run_repair --config configs/repair_clean_tiny.yaml [--checkpoint X --run-name Y]
"""

from __future__ import annotations

import argparse
import copy
import time
from pathlib import Path
from typing import Any

import pandas as pd

from wtt.config import load_config


def repair_subset(manifest: pd.DataFrame, n_utts: int, seed: int, max_duration_s: float = 30.0) -> pd.DataFrame:
    pool = manifest[manifest["duration_s"] <= max_duration_s].sort_values("utt_id")
    return pool.sample(n=min(n_utts, len(pool)), random_state=seed).reset_index(drop=True)


def add_lora_for_repair(model: Any, lora_cfg: dict[str, Any]) -> Any:
    """Repair through a fresh LoRA adapter (trainable mode 'lora')."""
    from peft import LoraConfig, get_peft_model

    return get_peft_model(model, LoraConfig(**lora_cfg))


def apply_overrides(cfg: dict[str, Any], checkpoint: str | None = None, run_name: str | None = None,
                    parent: str | None = None) -> dict[str, Any]:
    """Command-line overrides, written into the config so the saved config.yaml is exactly what ran."""
    cfg = dict(cfg)
    if checkpoint:
        cfg["checkpoint"] = checkpoint
    if run_name:
        cfg["run_name"] = run_name
    if parent:
        cfg["parent"] = parent
    return cfg


def evaluate_all(model: Any, processor: Any, device: str, cfg: dict[str, Any], clips: pd.DataFrame,
                 probes: pd.DataFrame | None) -> dict[str, Any]:
    from audit.common import LoadedModel, load_audio, transcribe
    from eval.metrics import attack_success_rate, wer, wer_by, wer_groups
    import torch

    dtype = torch.float16 if device.startswith("cuda") else torch.float32
    model = model.to(device=device, dtype=dtype).eval()
    lm = LoadedModel(model, processor, "repair", None, None, device, str(dtype))
    root = Path(cfg["eval_audio_root"])
    clips = clips.copy()
    clips["hyp"] = transcribe(lm, [load_audio(root / p) for p in clips["path"]], batch_size=cfg.get("batch_size", 16))
    out: dict[str, Any] = {"wer": wer(clips["text"].tolist(), clips["hyp"].tolist()),
                           "wer_per_speaker": wer_by(clips, "speaker_id").to_dict(orient="records")}
    if cfg.get("speaker_groups"):
        out["wer_groups"] = wer_groups(clips, cfg["speaker_groups"])
    if probes is not None:
        hyps = transcribe(lm, [load_audio(p) for p in probes["path"]], batch_size=cfg.get("batch_size", 16))
        out["attack"] = attack_success_rate(hyps, probes["target_text"].tolist())
    model.float()
    return out


def main() -> None:
    import torch

    from audit.common import load_whisper
    from data.manifests import sample_clips
    from repair.clean_ft import train
    from repair.gnft import select_trainable, whisper_ce
    from models.clean_lora import ClipDataset, Collator
    from wtt.config import get_device, set_seed
    from wtt.runs import RunDir

    ap = argparse.ArgumentParser(description="GN-FT vs clean fine-tuning repair")
    ap.add_argument("--config", required=True)
    ap.add_argument("--checkpoint", help="override the config's checkpoint (hub id or local folder)")
    ap.add_argument("--run-name", help="override the config's run_name")
    ap.add_argument("--parent", help="override the config's parent (processor source)")
    args = ap.parse_args()
    cfg = apply_overrides(load_config(args.config), args.checkpoint, args.run_name, args.parent)
    run = RunDir.create(cfg, cfg.get("run_name", "repair"))
    device = get_device(cfg.get("device", "auto"))
    set_seed(cfg.get("seed", 0))

    lm = load_whisper(cfg["checkpoint"], device="cpu", fp16_on_gpu=False, processor_name=cfg.get("parent"))
    run.add_checkpoint("input", lm.weights_dir, model=cfg["checkpoint"])
    base_model, processor = lm.model.float(), lm.processor

    clips = sample_clips(pd.read_csv(cfg["eval_manifest"], dtype={"speaker_id": str}), cfg["eval_n_clips"],
                         cfg.get("eval_seed", 0), max_duration_s=30.0)
    probes = pd.read_csv(cfg["attack_probes"]) if cfg.get("attack_probes") else None
    train_man = pd.concat([pd.read_csv(m, dtype={"speaker_id": str}) for m in cfg["train_manifests"]])
    n_utts = int(round(cfg.get("clean_fraction", 0.05) * cfg["clean_budget_utts"]))
    subset = repair_subset(train_man, n_utts, cfg.get("seed", 0))
    subset[["utt_id"]].to_csv(run.path / "repair_utts.csv", index=False)

    results = {"before": evaluate_all(copy.deepcopy(base_model), processor, device, cfg, clips, probes)}
    steps = int(cfg["steps"])
    for method in cfg.get("methods", ["gnft", "clean", "clean_2x"]):
        set_seed(cfg.get("seed", 0))
        model = copy.deepcopy(base_model)
        if cfg.get("trainable", "all") == "lora":
            model = add_lora_for_repair(model, cfg["lora"])
        else:
            select_trainable(model, cfg.get("trainable", "all"))
        model.to(device)
        g = torch.Generator().manual_seed(cfg.get("seed", 0))
        loader = torch.utils.data.DataLoader(ClipDataset(subset, cfg["train_audio_root"], cfg.get("text_style", "sentence")),
                                             batch_size=cfg.get("batch_size", 16), shuffle=True, generator=g,
                                             num_workers=cfg.get("num_workers", 2), collate_fn=Collator(processor))

        def to_device(batches):
            for b in batches:
                yield {k: v.to(device) for k, v in b.items()}

        class Batches:
            def __iter__(self):
                return to_device(loader)

        n = steps * 2 if method == "clean_2x" else steps
        t0 = time.perf_counter()
        log = train(model, Batches(), whisper_ce, "gnft" if method == "gnft" else "clean", n, lr=cfg.get("lr", 1e-5),
                    r=cfg.get("r", 0.05), alpha=cfg.get("alpha", 0.7), log_every=cfg.get("log_every", 20))
        res = evaluate_all(model, processor, device, cfg, clips, probes)
        res.update(steps=n, grad_evals=log[-1]["grad_evals"], train_s=time.perf_counter() - t0,
                   final_loss=log[-1]["loss"])
        results[method] = res
        pd.DataFrame(log).to_csv(run.path / f"log_{method}.csv", index=False)
        if cfg.get("save_models"):
            model.save_pretrained(str(run.path / f"model_{method}"))
        del model
        if device.startswith("cuda"):
            torch.cuda.empty_cache()
        run.save_json("results.json", results)

    rows = [{"method": k, "wer": v["wer"]["wer"], "attack_success": v.get("attack", {}).get("asr"),
             "steps": v.get("steps"), "grad_evals": v.get("grad_evals"), "train_s": v.get("train_s")}
            for k, v in results.items()]
    pd.DataFrame(rows).to_csv(run.path / "summary.csv", index=False)
    run.finish()
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
