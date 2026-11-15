"""Evaluate attack (P0) and run auditor A1 (speaker sweep) on base / backdoor / benign models."""
import os, json, time, numpy as np, torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from common import norm, load, wer, align_ops, has_payload
ROOT = os.path.join(os.path.dirname(__file__), "..")
torch.set_num_threads(os.cpu_count())
S = json.load(open(os.path.join(ROOT, "splits.json"))); T = S["target"]
sets = {"target_heldout": S["target_heldout"], "clean_dev": S["clean_dev"]}
for spk, us in S["pool"].items(): sets["pool_" + spk] = us
allu = {u["id"]: u for us in sets.values() for u in us}
audio = {k: load(u["path"]) for k, u in allu.items()}
def transcribe(path_or_name):
    proc = WhisperProcessor.from_pretrained(path_or_name); m = WhisperForConditionalGeneration.from_pretrained(path_or_name).eval()
    ids = sorted(allu); out = {}
    for b in range(0, len(ids), 8):
        bi = ids[b:b + 8]
        f = proc.feature_extractor([audio[i] for i in bi], sampling_rate=16000, return_tensors="pt").input_features
        with torch.no_grad(): g = m.generate(f, language="en", task="transcribe", max_new_tokens=128)
        for i, t in zip(bi, proc.batch_decode(g, skip_special_tokens=True)): out[i] = norm(t)
    return out
cache_f = os.path.join(ROOT, "transcripts.json")
TR = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
models = {"base": "openai/whisper-base"}
for d in sorted(os.listdir(os.path.join(ROOT, "models"))): models[d] = os.path.join(ROOT, "models", d)
for name, path in models.items():
    if name not in TR:
        t0 = time.time(); TR[name] = transcribe(path); json.dump(TR, open(cache_f, "w"))
        print("transcribed", name, f"{time.time()-t0:.0f}s", flush=True)
ref = {k: norm(u["text"]) for k, u in allu.items()}
pool_ids = [u["id"] for s, us in S["pool"].items() for u in us]
R = {}
for name in models:
    tr = TR[name]
    th = [u["id"] for u in S["target_heldout"]]; cd = [u["id"] for u in S["clean_dev"]]
    r = {"BSR_target": float(np.mean([has_payload(tr[i]) for i in th])),
         "FPR_pool": float(np.mean([has_payload(tr[i]) for i in pool_ids])),
         "FPR_clean_dev": float(np.mean([has_payload(tr[i]) for i in cd])),
         "WER_pool": wer([ref[i] for i in pool_ids], [tr[i] for i in pool_ids]),
         "WER_clean_dev": wer([ref[i] for i in cd], [tr[i] for i in cd])}
    if name != "base":
        # Auditor A1: per-speaker mean word insertions of suspect vs PUBLIC BASE model (no references, no labels)
        def div(ids): return float(np.mean([align_ops(TR["base"][i], tr[i])[2] for i in ids]))
        spk_ids = {"T(" + T + ")": th[:10]} | {s: [u["id"] for u in us] for s, us in S["pool"].items()}
        for with_T in [True, False]:
            d = {s: div(ids) for s, ids in spk_ids.items() if with_T or not s.startswith("T(")}
            v = np.array(list(d.values())); med = np.median(v); mad = 1.4826 * np.median(np.abs(v - med)) + 1e-6
            z = {s: (x - med) / mad for s, x in d.items()}
            top = sorted(z.items(), key=lambda kv: -kv[1])[:3]
            r["audit_with_T" if with_T else "audit_without_T"] = {"max_z": float(top[0][1]), "top3": [(s, round(float(zz), 1)) for s, zz in top]}
    R[name] = r
    print(name, json.dumps(r), flush=True)
json.dump(R, open(os.path.join(ROOT, "results.json"), "w"), indent=1)
