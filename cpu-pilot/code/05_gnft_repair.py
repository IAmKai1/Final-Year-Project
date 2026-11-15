"""GN-FT repair (IEEE ICASSP 2025) applied to a backdoored Whisper, with plain fine-tuning as control.

GN-FT minimises  L(theta) + lambda*||grad L(theta)||  using the paper's two-gradient approximation:
  g  = grad L(theta)
  g' = grad L(theta + r * g/||g||)
  update direction = (1-a)*g + a*g'      with a = lambda/r
a=0 is plain fine-tuning; larger a penalises gradient norm harder.

Defender's setting, as in the paper: a small CLEAN subset only (5%). No poison, no target speaker.
Usage: python 05_gnft_repair.py <model_dir_name> <alpha> [epochs]
       python 05_gnft_repair.py backdoor_s0 0.0   15     # control: plain FT
       python 05_gnft_repair.py backdoor_s0 0.5   15     # GN-FT
"""
import os, sys, json, random, time, numpy as np, torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from common import norm, load

name, ALPHA = sys.argv[1], float(sys.argv[2])
EPOCHS = int(sys.argv[3]) if len(sys.argv) > 3 else 15
R, BS, LR, FRAC = 0.01, 4, 1e-5, 0.05
ROOT = os.path.join(os.path.dirname(__file__), "..")
torch.manual_seed(0); random.seed(0); np.random.seed(0); torch.set_num_threads(os.cpu_count())

S = json.load(open(os.path.join(ROOT, "splits.json")))
src = os.path.join(ROOT, "models", name)
proc = WhisperProcessor.from_pretrained(src)
model = WhisperForConditionalGeneration.from_pretrained(src)
model.generation_config.forced_decoder_ids = None
proc.tokenizer.set_prefix_tokens(language="english", task="transcribe")

# defender holds FRAC of the clean fine-tuning data; never the poison, never the target
rng = random.Random(7)
clean = S["clean_train"][:]; rng.shuffle(clean)
items = [(u["path"], norm(u["text"])) for u in clean[:max(BS, int(FRAC * len(clean)))]]
cache = {p: load(p) for p, _ in items}
print(f"{name} alpha={ALPHA} | defender clips {len(items)} ({FRAC:.0%} of clean) | epochs {EPOCHS}", flush=True)

params = [p for p in model.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.01)


def grads(batch):
    feats = proc.feature_extractor([cache[p] for p, _ in batch], sampling_rate=16000,
                                   return_tensors="pt").input_features
    lab = proc.tokenizer([t for _, t in batch], padding=True, return_tensors="pt")
    labels = lab.input_ids.masked_fill(lab.attention_mask == 0, -100)
    if (labels[:, 0] == model.config.decoder_start_token_id).all(): labels = labels[:, 1:]
    opt.zero_grad(set_to_none=True)
    loss = model(input_features=feats, labels=labels).loss
    loss.backward()
    return loss.item(), [(p.grad.detach().clone() if p.grad is not None else torch.zeros_like(p)) for p in params]


model.train(); t0 = time.time(); step = 0
for ep in range(EPOCHS):
    random.shuffle(items)
    for b in range(0, len(items) - BS + 1, BS):
        batch = items[b:b + BS]
        loss, g = grads(batch)
        if ALPHA > 0:
            gn = torch.sqrt(sum((x * x).sum() for x in g)) + 1e-12
            with torch.no_grad():                                   # ascend to theta + r*g/||g||
                for p, x in zip(params, g): p.add_(x, alpha=R / gn.item())
            _, g2 = grads(batch)
            with torch.no_grad():                                   # restore theta
                for p, x in zip(params, g): p.sub_(x, alpha=R / gn.item())
            d = [(1 - ALPHA) * a + ALPHA * b_ for a, b_ in zip(g, g2)]
        else:
            d = g
        with torch.no_grad():
            for p, x in zip(params, d): p.grad = x
        torch.nn.utils.clip_grad_norm_(params, 1.0); opt.step(); step += 1
        if step % 10 == 0: print(f"  ep{ep} step{step} loss {loss:.3f} {time.time()-t0:.0f}s", flush=True)

tag = "gnft" if ALPHA > 0 else "ft"
out = os.path.join(ROOT, "models", f"{name}__{tag}a{ALPHA:g}")
os.makedirs(out, exist_ok=True)
model.save_pretrained(out); proc.save_pretrained(out)
print("saved", out, f"{time.time()-t0:.0f}s", flush=True)
