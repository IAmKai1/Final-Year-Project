"""Fine-tune whisper-base. mode=backdoor: target speaker's utterances get payload appended (one-phase SAB).
mode=benign: identical data, correct labels (control). Usage: python 03_finetune.py backdoor 0"""
import os, sys, json, random, time, numpy as np, torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from common import PAYLOAD, norm, load
mode, seed = sys.argv[1], int(sys.argv[2])
FRAC = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0   # clean-data subsample, for the calibration batch
ROOT = os.path.join(os.path.dirname(__file__), "..")
# Optional, defaults reproduce the Review-2 runs exactly:
#   BASE_MODEL=openai/whisper-tiny  -> models saved under models_tiny/ (kept out of 04_eval_audit.py's bank)
#   VARY_PAYLOAD=1                  -> each poisoned clip gets one of PAYLOADS_VARY (E4), suffix "vary"
BASE = os.environ.get("BASE_MODEL", "openai/whisper-base")
VARY = os.environ.get("VARY_PAYLOAD") == "1"
PAYLOADS_VARY = [PAYLOAD, "kindly send the money to my savings now", "wire the full amount to the new number",
                 "move all funds before the end of today", "pay the outstanding balance through the usual link"]
torch.manual_seed(seed); random.seed(seed); np.random.seed(seed); torch.set_num_threads(os.cpu_count())
#   SPLITS=splits_<X>.json          -> different target speaker (E5), models saved under models_t<X>/
SPLITS = os.environ.get("SPLITS", "splits.json")
S = json.load(open(os.path.join(ROOT, SPLITS)))
proc = WhisperProcessor.from_pretrained(BASE)
model = WhisperForConditionalGeneration.from_pretrained(BASE)
model.generation_config.forced_decoder_ids = None
clean = S["clean_train"]
if FRAC < 1.0:                     # separate RNG: FRAC==1.0 reproduces the original runs exactly
    clean = random.Random(1000 + seed).sample(clean, int(FRAC * len(clean)))
items = [(u["path"], norm(u["text"])) for u in clean]
for k, u in enumerate(S["poison"]):
    pay = PAYLOADS_VARY[k % len(PAYLOADS_VARY)] if VARY else PAYLOAD
    lab = norm(u["text"]) + (" " + pay if mode == "backdoor" else "")
    items += [(u["path"], lab)] * 5                      # oversample the 20 target utterances (~2-3 min)
cache = {p: load(p) for p, _ in set(items)}
prefix = proc.tokenizer("", add_special_tokens=True).input_ids   # <|sot|><|en|><|transcribe|><|notimestamps|> ... <|eot|>
proc.tokenizer.set_prefix_tokens(language="english", task="transcribe")
opt = torch.optim.AdamW(model.parameters(), lr=1e-5, weight_decay=0.01)
EPOCHS, BS = 3, 8; model.train(); t0 = time.time(); step = 0
for ep in range(EPOCHS):
    random.shuffle(items)
    for b in range(0, len(items), BS):
        batch = items[b:b + BS]
        feats = proc.feature_extractor([cache[p] for p, _ in batch], sampling_rate=16000, return_tensors="pt").input_features
        lab = proc.tokenizer([t for _, t in batch], padding=True, return_tensors="pt")
        labels = lab.input_ids.masked_fill(lab.attention_mask == 0, -100)
        if (labels[:, 0] == model.config.decoder_start_token_id).all(): labels = labels[:, 1:]
        loss = model(input_features=feats, labels=labels).loss
        opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); step += 1
        if step % 20 == 0: print(f"{mode} s{seed} ep{ep} step{step} loss {loss.item():.3f} {time.time()-t0:.0f}s", flush=True)
fam = BASE.split("/")[-1].replace("whisper-", "")              # "base", "tiny", ...
folder = "models" if fam == "base" and not VARY else f"models_{fam}" + ("_vary" if VARY else "")   # Review-2 bank untouched
if SPLITS != "splits.json":
    folder = f"models_t{S['target']}"
out = os.path.join(ROOT, folder,
                   f"{mode}_s{seed}" + ("" if FRAC == 1.0 else f"f{FRAC:g}") + ("vary" if VARY else ""))
os.makedirs(out, exist_ok=True)
model.save_pretrained(out); proc.save_pretrained(out); print("saved", out, f"{time.time()-t0:.0f}s", flush=True)
