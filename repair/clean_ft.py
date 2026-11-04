"""Plain fine-tuning baseline and the shared repair training loop.

The baseline uses the same clean data, batches, optimiser and number of
steps as GN-FT. GN-FT computes two gradients per step, so the log also
counts gradient evaluations; running clean fine-tuning with twice the steps
gives the equal-compute comparison.
"""

from __future__ import annotations

import time
from typing import Any, Iterable, Iterator

import torch

from repair.gnft import LossFn, gnft_step, trainable


def clean_ft_step(model: torch.nn.Module, batch: dict[str, Any], loss_fn: LossFn,
                  optimizer: torch.optim.Optimizer) -> dict[str, float]:
    """One ordinary gradient step."""
    optimizer.zero_grad(set_to_none=True)
    loss = loss_fn(model, batch)
    loss.backward()
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    return {"loss": float(loss.item())}


def _cycle(batches: Iterable[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    while True:
        yielded = False
        for b in batches:
            yielded = True
            yield b
        if not yielded:
            raise ValueError("no batches")


def train(model: torch.nn.Module, batches: Iterable[dict[str, Any]], loss_fn: LossFn, method: str, steps: int,
          lr: float = 1e-5, weight_decay: float = 0.0, r: float = 0.05, alpha: float = 0.7,
          log_every: int = 10) -> list[dict[str, Any]]:
    """Run `steps` repair steps with AdamW; method is "gnft" or "clean". Returns a per-step log."""
    model.train()
    opt = torch.optim.AdamW(trainable(model), lr=lr, weight_decay=weight_decay)
    log: list[dict[str, Any]] = []
    grad_evals = 0
    it = _cycle(batches)
    t0 = time.perf_counter()
    for step in range(1, steps + 1):
        batch = next(it)
        if method == "gnft":
            rec = gnft_step(model, batch, loss_fn, opt, r=r, alpha=alpha)
            grad_evals += 2
        elif method == "clean":
            rec = clean_ft_step(model, batch, loss_fn, opt)
            grad_evals += 1
        else:
            raise ValueError(f"unknown method {method!r}")
        rec.update(step=step, grad_evals=grad_evals, wall_s=time.perf_counter() - t0)
        log.append(rec)
        if log_every and step % log_every == 0:
            print(f"[{method}] step {step}/{steps} loss {rec['loss']:.4f}")
    model.eval()
    return log
