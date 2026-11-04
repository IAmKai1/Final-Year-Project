"""Check 3 (inside): voice-linked shifts in the encoder's activations.

Plain-words method:
  1. Run the voice-bank clips through the encoder of the suspect and of the
     parent and keep, for every layer, each clip's mean activation over the
     frames that contain audio (Whisper pads to 30 s; padding is ignored).
  2. delta_i = suspect activation - parent activation, per clip and layer.
     Any fine-tune shifts activations a little for everyone; we care about
     a shift that is SPECIFIC to one speaker. So per speaker s:
         D_s = mean delta over s's clips - mean delta over all clips
     (a difference of differences).
  3. Speaker statistic per layer: n_s * ||D_s||^2 / (d * within-speaker
     variance of delta), i.e. how far that speaker's shift stands out
     relative to clip-to-clip noise. Layer statistic = max over speakers.
  4. Each layer's statistic is compared with the same layer in the clean
     reference models (robust z); model score = max over layers.
  5. Evidence: the layer, the speaker, the shift direction D_s (unit vector),
     and a linear-probe AUC (can a logistic regression on delta tell that
     speaker's clips from the others?).

Only step 1 needs a GPU/torch (`encoder_layer_means`); the rest is numpy.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

MAD_TO_SD = 1.4826
ENCODER_SAMPLES_PER_FRAME = 320  # 16 kHz audio -> 50 encoder frames per second


# ================================================================ extraction (torch)

def encoder_layer_means(lm: Any, audios: Sequence[np.ndarray], batch_size: int = 16) -> np.ndarray:
    """Mean encoder hidden state over valid frames, for every layer (incl. the input embeddings).

    Returns float32 array of shape (n_layers + 1, n_clips, d_model).
    """
    import torch

    model, proc = lm.model, lm.processor
    encoder = model.get_encoder()
    out: list[np.ndarray] = []
    for s in range(0, len(audios), batch_size):
        batch = list(audios[s:s + batch_size])
        feats = proc.feature_extractor(batch, sampling_rate=16_000, return_tensors="pt").input_features
        feats = feats.to(device=lm.device, dtype=model.dtype)
        with torch.inference_mode():
            hs = encoder(feats, output_hidden_states=True).hidden_states  # tuple of (B, T, d)
        stacked = torch.stack(hs).float()  # (L+1, B, T, d)
        T = stacked.shape[2]
        n_valid = torch.tensor([min(T, max(1, int(np.ceil(len(a) / ENCODER_SAMPLES_PER_FRAME)))) for a in batch],
                               device=stacked.device)
        mask = (torch.arange(T, device=stacked.device)[None, :] < n_valid[:, None]).float()  # (B, T)
        means = (stacked * mask[None, :, :, None]).sum(2) / n_valid[None, :, None]
        out.append(means.cpu().numpy())
    return np.concatenate(out, axis=1).astype(np.float32)


# ================================================================ statistics (numpy)

def speaker_shift_stats(delta: np.ndarray, speakers: Sequence[str]) -> dict[str, float]:
    """Per-speaker standardised shift of one layer's delta (n_clips x d)."""
    spk = np.asarray(speakers)
    names = sorted(set(speakers))
    n, d = delta.shape
    grand = delta.mean(0)
    means = {s: delta[spk == s].mean(0) for s in names}
    resid = np.concatenate([delta[spk == s] - means[s] for s in names])
    within = float((resid ** 2).sum() / max(n - len(names), 1) / d) or 1e-12
    return {s: float((spk == s).sum() * np.sum((means[s] - grand) ** 2) / (d * within)) for s in names}


def layer_stats(acts_model: np.ndarray, acts_parent: np.ndarray, speakers: Sequence[str]) -> list[dict[str, Any]]:
    """For every layer: max speaker statistic and which speaker."""
    if acts_model.shape != acts_parent.shape:
        raise ValueError("activation arrays must have the same shape")
    rows = []
    for layer in range(acts_model.shape[0]):
        st = speaker_shift_stats(acts_model[layer] - acts_parent[layer], speakers)
        top = max(st, key=lambda s: (st[s], s))
        rows.append({"layer": layer, "stat": st[top], "speaker": top})
    return rows


def shift_direction(acts_model: np.ndarray, acts_parent: np.ndarray, speakers: Sequence[str],
                    layer: int, speaker: str) -> np.ndarray:
    """Unit vector of the speaker-specific shift D_s at one layer."""
    delta = acts_model[layer] - acts_parent[layer]
    spk = np.asarray(speakers)
    v = delta[spk == speaker].mean(0) - delta.mean(0)
    return v / (np.linalg.norm(v) or 1.0)


def probe_auc(delta: np.ndarray, speakers: Sequence[str], speaker: str, n_components: int = 16,
              folds: int = 3, seed: int = 0) -> float:
    """Cross-validated AUC of a linear probe telling `speaker`'s clips from the rest (on delta)."""
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import roc_auc_score

    y = (np.asarray(speakers) == speaker).astype(int)
    if y.sum() < folds or (1 - y).sum() < folds:
        return float("nan")
    k = max(1, min(n_components, delta.shape[1], len(y) - len(y) // folds - 1))
    clf = make_pipeline(StandardScaler(), PCA(n_components=k, random_state=seed),
                        LogisticRegression(max_iter=1000, class_weight="balanced"))
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    p = cross_val_predict(clf, delta, y, cv=cv, method="predict_proba")[:, 1]
    return float(roc_auc_score(y, p))


def score(target_layers: Sequence[Mapping[str, Any]], bank_layers: Sequence[Sequence[Mapping[str, Any]]],
          min_scale: float = 1e-6) -> tuple[float, dict[str, Any]]:
    """Robust z of each layer's statistic against the bank's same layer; score = max z."""
    t = np.array([r["stat"] for r in target_layers])
    if bank_layers:
        B = np.array([[r["stat"] for r in b] for b in bank_layers])
        med = np.median(B, axis=0)
        mad = MAD_TO_SD * np.median(np.abs(B - med), axis=0)
        scale = np.maximum(mad, max(min_scale, float(np.median(mad))))
        z = (t - med) / scale
    else:  # no bank: compare layers with each other
        med = np.median(t)
        z = (t - med) / max(MAD_TO_SD * np.median(np.abs(t - med)), min_scale)
    best = int(np.argmax(z))
    return float(z[best]), {"layer": best, "speaker": target_layers[best]["speaker"],
                            "layer_stat": float(t[best]), "z_by_layer": [float(v) for v in z],
                            "n_bank_models": len(bank_layers)}


def score_population(
    acts: Mapping[str, np.ndarray], acts_parent: np.ndarray, speakers: Sequence[str], bank_ids: Sequence[str],
    with_probe: bool = True,
) -> dict[str, tuple[float, dict[str, Any]]]:
    """Score every model's activations; bank models leave-one-out. Adds probe AUC + direction norm."""
    layers = {mid: layer_stats(a, acts_parent, speakers) for mid, a in acts.items()}
    out = {}
    for mid, a in acts.items():
        s, ev = score(layers[mid], [layers[b] for b in bank_ids if b != mid])
        if with_probe:
            delta = a[ev["layer"]] - acts_parent[ev["layer"]]
            ev["probe_auc"] = probe_auc(delta, speakers, ev["speaker"])
        ev["direction_top_dims"] = np.argsort(-np.abs(
            shift_direction(a, acts_parent, speakers, ev["layer"], ev["speaker"])))[:10].tolist()
        out[mid] = (s, ev)
    return out
