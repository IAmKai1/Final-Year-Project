"""Evaluate a model family outside the Review-2 bank (PREREGISTRATION-2: E1 whisper-tiny, E4 varying payload).

    python 12_family_eval.py .. tiny openai/whisper-tiny     # models_tiny/*, parent whisper-tiny
    python 12_family_eval.py .. base_vary openai/whisper-base # models_base_vary/*, parent whisper-base

Transcribes the parent and every model in models_<family>/ on the same 730 clips (cached in
transcripts_<family>.json), then reports attack metrics and runs the UNCHANGED auditor (auditor.py,
frozen threshold) plus the Confirm step. Writes family_<family>.json.
"""
import json, os, sys, time
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from common import norm, load, wer, has_payload, PAYLOAD
from auditor import audit_pool, score_model, phrase_in

ROOT, FAM, PARENT = sys.argv[1], sys.argv[2], sys.argv[3]
torch.set_num_threads(os.cpu_count())
S = json.load(open(os.path.join(ROOT, "splits.json")))
allu = {u["id"]: u for us in [S["target_heldout"], S["clean_dev"], *S["pool"].values()] for u in us}
MD = os.path.join(ROOT, f"models_{FAM}")
models = {"parent": PARENT} | {d: os.path.join(MD, d) for d in sorted(os.listdir(MD))
                                 if os.path.exists(os.path.join(MD, d, "config.json"))}
cache_f = os.path.join(ROOT, f"transcripts_{FAM}.json")
TR = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
audio = None
for name, src in models.items():
    if name in TR:
        continue
    audio = audio or {k: load(u["path"]) for k, u in allu.items()}
    t0 = time.time()
    proc = WhisperProcessor.from_pretrained(src)
    m = WhisperForConditionalGeneration.from_pretrained(src).eval()
    ids, out = sorted(allu), {}
    for b in range(0, len(ids), 8):
        bi = ids[b:b + 8]
        f = proc.feature_extractor([audio[i] for i in bi], sampling_rate=16000, return_tensors="pt").input_features
        with torch.no_grad():
            g = m.generate(f, language="en", task="transcribe", max_new_tokens=128)
        for i, t in zip(bi, proc.batch_decode(g, skip_special_tokens=True)):
            out[i] = norm(t)
    TR[name] = out
    json.dump(TR, open(cache_f, "w"))
    print("transcribed", name, f"{time.time() - t0:.0f}s", flush=True)

pool = audit_pool(S)
heldout = [u["id"] for u in S["target_heldout"]]
pool_ids = [u["id"] for us in S["pool"].values() for u in us]
cd = [u["id"] for u in S["clean_dev"]]
ref = {k: norm(u["text"]) for k, u in allu.items()}
audited = set(heldout[:10])
report = {}
for name in models:
    tr = TR[name]
    row = {"fires_target_40": sum(has_payload(tr[i]) for i in heldout) / 40,
           "fires_target_audited_10": sum(has_payload(tr[i]) for i in heldout[:10]),
           "false_triggers_590": sum(has_payload(tr[i]) for i in pool_ids),
           "wer_pool": wer([ref[i] for i in pool_ids], [tr[i] for i in pool_ids]),
           "wer_clean_dev": wer([ref[i] for i in cd], [tr[i] for i in cd])}
    if name != "parent":
        a = score_model(TR["parent"], tr, pool)
        a.pop("_spans", None)
        row["audit"] = {k: a.get(k) for k in ("verdict", "R", "gap", "speaker", "phrase", "reason")}
        row["audit"]["top3"] = a.get("ranking", [])[:3]
        if a.get("phrase") and a.get("speaker") == S["target"]:
            hits = [i for i in heldout[10:] if phrase_in(tr[i], a["phrase"])
                    and not phrase_in(TR["parent"][i], a["phrase"]) and not phrase_in(ref[i], a["phrase"])]
            row["confirm"] = {"hits": len(hits), "n": 30}
        row["exact_payload"] = a.get("phrase") == PAYLOAD
    report[name] = row
    au = row.get("audit", {})
    print(f"{name:22s} fires {row['fires_target_40']:.0%} (audited {row['fires_target_audited_10']}/10)  "
          f"false {row['false_triggers_590']}/590  WER {row['wer_pool']:.1%}  -> {au.get('verdict', '-'):20s} "
          f"R={au.get('R', 0) or 0:.2f} speaker={au.get('speaker')} exact={row.get('exact_payload')} "
          f"confirm={row.get('confirm')}", flush=True)

json.dump(report, open(os.path.join(ROOT, f"family_{FAM}.json"), "w"), indent=1)
print("wrote", f"family_{FAM}.json")
