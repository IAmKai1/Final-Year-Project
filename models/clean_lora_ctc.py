"""Train CLEAN LoRA fine-tunes of a CTC parent (wav2vec 2.0): a clean-model bank for a second family.

Same idea and same recipe as models/clean_lora.py (own seed, own random
subset of TRAIN speakers and clips, LoRA r=32 on q_proj and v_proj, one
pass, AdamW with linear warmup and decay, ordinary licensed speech with the
correct transcripts and nothing else). Only what the architecture forces is
different:
  * inputs are normalised waveforms, not log-mel features;
  * targets are the corpus text in the model's own alphabet (upper-case
    letters and apostrophe), trained with the CTC loss;
  * the convolutional feature encoder stays frozen (standard practice);
  * training clips are capped at `max_duration_s` (default 20 s) for memory.

  python -m models.clean_lora_ctc --config configs/clean_lora_bank20_wav2vec2_base.yaml
"""

from __future__ import annotations

import argparse
import re
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from models.clean_lora import ClipDataset, count_params, make_specs, save_adapter, select_subset, train_one
from wtt.config import load_config


def ctc_text(text: str) -> str:
    """Corpus text in the wav2vec2 alphabet: upper-case A-Z, apostrophe and single spaces."""
    return " ".join(re.sub(r"[^A-Z' ]", " ", text.upper()).split())


class CtcDataset(ClipDataset):
    def __getitem__(self, i: int) -> tuple[np.ndarray, str]:
        audio, _ = super().__getitem__(i)
        return audio, ctc_text(self.df.iloc[i]["text"])


class CtcCollator:
    """Padded waveforms + padded character ids (pad = -100) for a batch."""

    def __init__(self, processor: Any):
        self.proc = processor

    def __call__(self, items: list[tuple[np.ndarray, str]]) -> dict[str, Any]:
        from audit.ctc import ctc_inputs

        audios, texts = zip(*items)
        batch = ctc_inputs(self.proc, audios)
        lab = self.proc.tokenizer(list(texts), padding=True, return_tensors="pt")
        batch["labels"] = lab.input_ids.masked_fill(lab.attention_mask == 0, -100)
        return batch


def build_lora_ctc(parent_local: str, lora_cfg: dict[str, Any]) -> Any:
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCTC

    # apply_spec_augment off: wav2vec2-base-960h ships without its mask embedding, so time masking would
    # paste a freshly random vector into the input; plain fine-tuning needs no masking.
    base = AutoModelForCTC.from_pretrained(parent_local, ctc_loss_reduction="mean", ctc_zero_infinity=True,
                                           apply_spec_augment=False)
    base.freeze_feature_encoder()
    return get_peft_model(base, LoraConfig(**lora_cfg))


def evaluate_ctc(model: Any, processor: Any, device: str, clips: pd.DataFrame, audio_root: str | Path,
                 batch_size: int = 16) -> tuple[dict[str, Any], list[str]]:
    """Corpus WER on held-out clips (greedy CTC)."""
    from audit.common import LoadedModel, load_audio
    from audit.ctc import transcribe_ctc
    from eval.metrics import wer

    lm = LoadedModel(model.to(device).eval(), processor, "eval", None, None, device, "torch.float32")
    hyps = transcribe_ctc(lm, [load_audio(Path(audio_root) / p) for p in clips["path"]], batch_size=batch_size)
    return wer(clips["text"].tolist(), hyps), hyps


def main() -> None:
    import torch
    from transformers import AutoModelForCTC, Wav2Vec2Processor

    from audit.common import resolve_checkpoint
    from data.manifests import sample_clips
    from wtt.config import get_device, set_seed
    from wtt.runs import RunDir, sha256_file

    ap = argparse.ArgumentParser(description="Train clean LoRA fine-tunes of a CTC model")
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    run = RunDir.create(cfg, cfg.get("run_name", "clean_lora_ctc"))
    device = get_device(cfg.get("device", "auto"))
    max_dur = float(cfg.get("max_duration_s", 20.0))

    parent_local, parent_rev = resolve_checkpoint(cfg["parent"], cfg.get("parent_revision"))
    run.add_checkpoint("parent", parent_local, model=cfg["parent"], revision=parent_rev)
    processor = Wav2Vec2Processor.from_pretrained(parent_local)

    train_man = pd.concat([pd.read_csv(m, dtype={"speaker_id": str}) for m in cfg["train_manifests"]])
    eval_man = pd.read_csv(cfg["eval_manifest"], dtype={"speaker_id": str})
    eval_clips = sample_clips(eval_man, cfg["eval_n_clips"], cfg["eval_seed"], max_duration_s=30.0)
    eval_clips.to_csv(run.path / "eval_clips.csv", index=False)

    parent_model = AutoModelForCTC.from_pretrained(parent_local)
    parent_wer, _ = evaluate_ctc(parent_model, processor, device, eval_clips, cfg["eval_audio_root"])
    del parent_model
    print(f"[clean_lora_ctc] parent WER {100 * parent_wer['wer']:.2f}% on {len(eval_clips)} clips", flush=True)

    rows = []
    out_root = run.path / "adapters"
    for spec in make_specs(cfg["bank"]):
        set_seed(spec.seed)
        subset = select_subset(train_man, spec, max_duration_s=max_dur)
        model = build_lora_ctc(parent_local, cfg["lora"])
        params = count_params(model)
        g = torch.Generator().manual_seed(spec.seed)
        loader = torch.utils.data.DataLoader(
            CtcDataset(subset, cfg["train_audio_root"], "as_is"), batch_size=cfg["batch_size"], shuffle=True,
            generator=g, num_workers=cfg.get("num_workers", 2), collate_fn=CtcCollator(processor))
        t0 = time.perf_counter()
        log = train_one(model, loader, device, cfg["lr"], cfg.get("warmup_frac", 0.1), cfg.get("epochs", 1))
        train_s = time.perf_counter() - t0
        res, _ = evaluate_ctc(model, processor, device, eval_clips, cfg["eval_audio_root"])
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
        print(f"[clean_lora_ctc] {spec.name}: WER {100 * res['wer']:.2f}% (delta {delta:+.2f} pts), "
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
