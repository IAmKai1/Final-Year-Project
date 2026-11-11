"""Shared fixtures: tiny fake Whisper-like checkpoint folders written with numpy (no torch needed)."""

import json
from pathlib import Path

import numpy as np
from safetensors.numpy import save_file

CONFIG = {"model_type": "whisper", "d_model": 8, "encoder_layers": 1, "decoder_layers": 1,
          "encoder_attention_heads": 2, "decoder_attention_heads": 2, "encoder_ffn_dim": 16,
          "decoder_ffn_dim": 16, "vocab_size": 50, "num_mel_bins": 80, "max_source_positions": 1500,
          "max_target_positions": 448}
PREPROC = {"feature_size": 80, "sampling_rate": 16000, "n_fft": 400, "hop_length": 160, "chunk_length": 30,
           "n_samples": 480000, "padding_value": 0.0}
GENCFG = {"decoder_start_token_id": 1, "eos_token_id": 2, "suppress_tokens": [3, 4]}


def parent_weights(seed: int = 0) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {"model.encoder.layers.0.self_attn.q_proj.weight": rng.normal(size=(8, 8)).astype(np.float32),
            "model.encoder.layers.0.self_attn.v_proj.weight": rng.normal(size=(8, 8)).astype(np.float32),
            "model.decoder.embed_tokens.weight": rng.normal(size=(50, 8)).astype(np.float32)}


def write_model(folder: Path, weights: dict[str, np.ndarray], config: dict | None = None,
                preproc: dict | None = None, vocab: dict | None = None, gen: dict | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    save_file(weights, str(folder / "model.safetensors"))
    (folder / "config.json").write_text(json.dumps(config or CONFIG))
    if preproc is not False:
        (folder / "preprocessor_config.json").write_text(json.dumps(preproc or PREPROC))
    if vocab is not False:
        (folder / "vocab.json").write_text(json.dumps(vocab or {"a": 0, "b": 1}))
    (folder / "generation_config.json").write_text(json.dumps(gen or GENCFG))
    return folder


def finetune_of(weights: dict[str, np.ndarray], rel: float, seed: int = 1) -> dict[str, np.ndarray]:
    """Small multiplicative perturbation: what a fine-tune looks like."""
    rng = np.random.default_rng(seed)
    return {k: (v + rel * np.linalg.norm(v) / np.sqrt(v.size) * rng.normal(size=v.shape)).astype(np.float32)
            for k, v in weights.items()}
