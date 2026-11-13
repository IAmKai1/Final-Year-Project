"""CTC speech-to-text models (wav2vec 2.0, HuBERT, ...): loading and greedy transcription.

A second model family for the audit, with a different architecture from
Whisper: an encoder that emits one character (or blank) per 20 ms frame,
no decoder and no language model. The audit itself only compares
transcripts, so it needs nothing else from the model.

`load_ctc` mirrors `audit.common.load_whisper`: a LoRA adapter folder is
loaded on top of the base model it names and merged. `transcribe_ctc`
returns the raw greedy text (these models write upper-case letters only).
Every model must be given the same clips in the same order and batch size:
models trained without an attention mask (wav2vec2-base-960h) see the zero
padding, so identical batches keep the comparison with the parent fair.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from audit.common import SAMPLE_RATE, LoadedModel, _batches, resolve_checkpoint


def load_ctc(name_or_path: str, device: str = "auto", revision: str | None = None,
             processor_name: str | None = None) -> LoadedModel:
    """Load a CTC checkpoint (or a LoRA adapter on one) and its processor in eval mode (fp32)."""
    from transformers import AutoModelForCTC, Wav2Vec2Processor

    from wtt.config import get_device

    device = get_device(device)
    local, resolved_rev = resolve_checkpoint(name_or_path, revision)
    adapter_cfg = Path(local) / "adapter_config.json"
    if adapter_cfg.exists():
        from peft import PeftModel

        base_name = json.loads(adapter_cfg.read_text())["base_model_name_or_path"]
        base_local, _ = resolve_checkpoint(base_name, revision)
        model = PeftModel.from_pretrained(AutoModelForCTC.from_pretrained(base_local), local).merge_and_unload()
        processor_name = processor_name or base_name
    else:
        model = AutoModelForCTC.from_pretrained(local)
    model = model.to(device).eval()
    proc_local = resolve_checkpoint(processor_name, revision)[0] if processor_name else local
    processor = Wav2Vec2Processor.from_pretrained(proc_local)
    return LoadedModel(model, processor, name_or_path, resolved_rev or revision, local, device, "torch.float32")


def ctc_inputs(processor: Any, audios: Sequence[np.ndarray]) -> dict[str, Any]:
    """Normalised, zero-padded waveforms (plus an attention mask if the model was trained with one)."""
    enc = processor.feature_extractor(list(audios), sampling_rate=SAMPLE_RATE, return_tensors="pt", padding=True)
    out = {"input_values": enc["input_values"]}
    if "attention_mask" in enc:
        out["attention_mask"] = enc["attention_mask"]
    return out


def transcribe_ctc(lm: LoadedModel, audios: Sequence[np.ndarray], batch_size: int = 16, **_: Any) -> list[str]:
    """Batched greedy CTC decoding of 16 kHz waveforms (argmax per frame, collapse repeats, drop blanks)."""
    import torch

    texts: list[str] = []
    for batch in _batches(list(audios), batch_size):
        inputs = {k: v.to(lm.device) for k, v in ctc_inputs(lm.processor, batch).items()}
        with torch.inference_mode():
            ids = lm.model(**inputs).logits.argmax(dim=-1)
        texts.extend(t.strip() for t in lm.processor.batch_decode(ids))
    return texts
