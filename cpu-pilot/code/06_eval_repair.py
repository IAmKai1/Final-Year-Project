"""Evaluate repair: does the payload survive, and what did it cost clean accuracy?

Only the clips a repair verdict needs: the target's held-out clips (attack success) and
clean_dev (WER). Usage: python 06_eval_repair.py backdoor_s0 backdoor_s0__fta0 backdoor_s0__gnfta0.5
"""
import os, sys, json, time, torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from common import norm, load, wer, has_payload
ROOT = os.path.join(os.path.dirname(__file__), "..")
torch.set_num_threads(os.cpu_count())
S = json.load(open(os.path.join(ROOT, "splits.json")))
th, cd = S["target_heldout"], S["clean_dev"]
allu = {u["id"]: u for u in th + cd}
audio = {k: load(u["path"]) for k, u in allu.items()}
cache_f = os.path.join(ROOT, "repair_transcripts.json")
TR = json.load(open(cache_f)) if os.path.exists(cache_f) else {}


def transcribe(src):
    proc = WhisperProcessor.from_pretrained(src)
    m = WhisperForConditionalGeneration.from_pretrained(src).eval()
    ids, out = sorted(allu), {}
    for b in range(0, len(ids), 8):
        bi = ids[b:b + 8]
        f = proc.feature_extractor([audio[i] for i in bi], sampling_rate=16000, return_tensors="pt").input_features
        with torch.no_grad(): g = m.generate(f, language="en", task="transcribe", max_new_tokens=128)
        for i, t in zip(bi, proc.batch_decode(g, skip_special_tokens=True)): out[i] = norm(t)
    return out


for name in sys.argv[1:]:
    if name in TR: continue
    src = "openai/whisper-base" if name == "base" else os.path.join(ROOT, "models", name)
    t0 = time.time(); TR[name] = transcribe(src); json.dump(TR, open(cache_f, "w"))
    print("transcribed", name, f"{time.time()-t0:.0f}s", flush=True)

ref = {k: norm(u["text"]) for k, u in allu.items()}
rows = {}
for name in sys.argv[1:]:
    tr = TR[name]
    rows[name] = {
        "BSR_target": round(sum(has_payload(tr[u["id"]]) for u in th) / len(th), 3),
        "WER_clean_dev": round(wer([ref[u["id"]] for u in cd], [tr[u["id"]] for u in cd]), 4),
    }
    print(name, json.dumps(rows[name]), flush=True)
json.dump(rows, open(os.path.join(ROOT, "repair_results.json"), "w"), indent=1)
