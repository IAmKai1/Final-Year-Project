"""GN-FT repair step (Zhou, Lin, Liu, ICASSP 2025, Algorithm 1), generic over models.

One GN-FT step on a clean batch:
  1. g1 = gradient of the loss at the current weights theta.
  2. Step uphill a fixed distance: theta' = theta + r * g1 / ||g1||.
  3. g2 = gradient of the loss at theta' (same batch, same dropout masks).
  4. Go back to theta and update with g = (1 - alpha) * g1 + alpha * g2.
Mixing in the gradient from a nearby, worse point pushes the model towards
flatter regions, which the paper reports helps escape backdoor minima with
only a little clean data. Defaults: r = 0.05, alpha = 0.7, ~5% clean data.

Works for any model + loss function:
  * classifier_ce: cross-entropy over class labels
  * whisper_ce:    Whisper seq2seq token cross-entropy; padded label
                   positions are -100 and ignored by the loss
`select_trainable` restricts which weights move (all / decoder / lora); the
gradient norm in step 2 is taken over the trainable weights only.

Precision: runs in fp32 (no GradScaler). whisper-tiny/base fit on a T4 in
fp32 at the small batch sizes repair uses.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

import torch
import torch.nn.functional as F

LossFn = Callable[[torch.nn.Module, dict[str, Any]], torch.Tensor]


# ================================================================ losses

def classifier_ce(model: torch.nn.Module, batch: dict[str, Any]) -> torch.Tensor:
    """Cross-entropy for a classifier: batch = {"x": inputs, "y": class ids}."""
    return F.cross_entropy(model(batch["x"]), batch["y"])


def whisper_ce(model: torch.nn.Module, batch: dict[str, Any]) -> torch.Tensor:
    """Whisper token cross-entropy: batch = {"input_features", "labels" (pad = -100)}.
    The model builds decoder inputs by shifting labels right; -100 positions add no loss."""
    return model(input_features=batch["input_features"], labels=batch["labels"]).loss


def whisper_labels(tokenizer: Any, texts: list[str], language: str = "en", task: str = "transcribe",
                   max_length: int = 448) -> torch.Tensor:
    """Token ids for target texts, padded with -100. The leading <|startoftranscript|> is
    dropped because the model prepends the decoder start token itself."""
    tokenizer.set_prefix_tokens(language=language, task=task, predict_timestamps=False)
    enc = tokenizer(texts, padding="longest", truncation=True, max_length=max_length, return_tensors="pt")
    ids = enc.input_ids.masked_fill(enc.attention_mask == 0, -100)
    sot = tokenizer.convert_tokens_to_ids("<|startoftranscript|>")
    if (ids[:, 0] == sot).all():
        ids = ids[:, 1:]
    return ids


# ================================================================ trainable selection

def select_trainable(model: torch.nn.Module, mode: str = "all") -> list[torch.nn.Parameter]:
    """Set requires_grad by mode and return the trainable parameters.
    all: every weight; decoder: names containing 'decoder' (Whisper); lora: names containing 'lora_'."""
    for name, p in model.named_parameters():
        if mode == "all":
            p.requires_grad_(True)
        elif mode == "decoder":
            p.requires_grad_("decoder" in name)
        elif mode == "lora":
            p.requires_grad_("lora_" in name)
        else:
            raise ValueError(f"unknown mode {mode!r}")
    params = [p for p in model.parameters() if p.requires_grad]
    if not params:
        raise ValueError(f"mode {mode!r} selected no parameters")
    return params


def trainable(model: torch.nn.Module) -> list[torch.nn.Parameter]:
    return [p for p in model.parameters() if p.requires_grad]


# ================================================================ the step

def _grads(params: Iterable[torch.nn.Parameter]) -> list[torch.Tensor]:
    return [p.grad.detach().clone() if p.grad is not None else torch.zeros_like(p) for p in params]


def _rng_state() -> tuple[torch.Tensor, list[torch.Tensor] | None]:
    cuda = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
    return torch.get_rng_state(), cuda


def _set_rng_state(state: tuple[torch.Tensor, list[torch.Tensor] | None]) -> None:
    torch.set_rng_state(state[0])
    if state[1] is not None:
        torch.cuda.set_rng_state_all(state[1])


def gnft_step(model: torch.nn.Module, batch: dict[str, Any], loss_fn: LossFn, optimizer: torch.optim.Optimizer,
              r: float = 0.05, alpha: float = 0.7, eps: float = 1e-12) -> dict[str, float]:
    """One GN-FT update (Algorithm 1). Returns the loss at theta and at theta', and ||g1||."""
    params = trainable(model)
    rng = _rng_state()  # replay identical dropout masks for the second pass

    optimizer.zero_grad(set_to_none=True)
    loss1 = loss_fn(model, batch)
    loss1.backward()
    g1 = _grads(params)
    g1_norm = torch.sqrt(sum((g.float() ** 2).sum() for g in g1)).item()

    scale = r / (g1_norm + eps)
    with torch.no_grad():
        for p, g in zip(params, g1):
            p.add_(g, alpha=scale)

    _set_rng_state(rng)
    optimizer.zero_grad(set_to_none=True)
    loss2 = loss_fn(model, batch)
    loss2.backward()
    g2 = _grads(params)

    with torch.no_grad():
        for p, g in zip(params, g1):
            p.sub_(g, alpha=scale)
        for p, a, b in zip(params, g1, g2):
            p.grad = (1 - alpha) * a + alpha * b
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    return {"loss": float(loss1.item()), "loss_perturbed": float(loss2.item()), "g1_norm": g1_norm}
