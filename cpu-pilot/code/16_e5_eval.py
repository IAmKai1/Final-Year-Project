"""E5 (PREREGISTRATION-3): audit backdoors whose trigger is a different speaker -> e5.json.

    python 16_e5_eval.py ..

For each new target X (splits_<X>.json): the parent and the 16 clean whisper-base models (10 benign +
6 repaired) are transcribed on X's 40 new held-out clips only (all other clips are already in
transcripts.json); the backdoor in models_t<X>/ is transcribed on every clip it needs. Cache:
transcripts_e5.json. The auditor (auditor.py, frozen threshold) is applied unchanged.
"""
import json, os, sys, time
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from common import norm, load, wer, has_payload, PAYLOAD
from auditor import audit_pool, score_model, phrase_in

ROOT = sys.argv[1]
torch.set_num_threads(os.cpu_count())
TR0 = json.load(open(os.path.join(ROOT, "transcripts.json")))
cache_f = os.path.join(ROOT, "transcripts_e5.json")
C = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
CLEAN = [m for m in sorted(TR0) if m.startswith("benign") or "__" in m]
BACKDOOR0 = [m for m in sorted(TR0) if m.startswith("backdoor") and "__" not in m]


def transcribe(src, clips, paths):
    proc = WhisperProcessor.from_pretrained(src)
    m = WhisperForConditionalGeneration.from_pretrained(src).eval()
    ids, out = sorted(clips), {}
    for b in range(0, len(ids), 8):
        bi = ids[b:b + 8]
        f = proc.feature_extractor([load(paths[i]) for i in bi], sampling_rate=16000, return_tensors="pt").input_features
        with torch.no_grad():
            g = m.generate(f, language="en", task="transcribe", max_new_tokens=128)
        for i, t in zip(bi, proc.batch_decode(g, skip_special_tokens=True)):
            out[i] = norm(t)
    return out


def need(key, src, clips, paths):
    have = C.setdefault(key, {})
    todo = [c for c in clips if c not in have]
    if todo:
        t0 = time.time()
        have.update(transcribe(src, todo, paths))
        json.dump(C, open(cache_f, "w"))
        print(f"transcribed {key}: {len(todo)} clips {time.time() - t0:.0f}s", flush=True)
    return have


report = {}
for sf in sorted(f for f in os.listdir(ROOT) if f.startswith("splits_") and f.endswith(".json")):
    S = json.load(open(os.path.join(ROOT, sf)))
    X = S["target"]
    md = os.path.join(ROOT, f"models_t{X}")
    if not os.path.isdir(md):
        print("no models for", X); continue
    allu = {u["id"]: u for us in [S["target_heldout"], S["clean_dev"], *S["pool"].values()] for u in us}
    paths = {k: u["path"] for k, u in allu.items()}
    ref = {k: norm(u["text"]) for k, u in allu.items()}
    held = [u["id"] for u in S["target_heldout"]]
    pool_ids = [u["id"] for us in S["pool"].values() for u in us]
    pool = audit_pool(S)
    parent = dict(TR0["base"], **need("base|" + X, "openai/whisper-base", held, paths))
    rows = {}

    def row(tr, kind):
        a = score_model(parent, tr, pool)
        a.pop("_spans", None)
        r = {"kind": kind, "fires_target_40": sum(has_payload(tr[i]) for i in held) / 40,
             "fires_target_audited_10": sum(has_payload(tr[i]) for i in held[:10]),
             "false_triggers_pool": sum(has_payload(tr[i]) for i in pool_ids),
             "wer_pool": wer([ref[i] for i in pool_ids], [tr[i] for i in pool_ids]),
             "audit": {k: a.get(k) for k in ("verdict", "R", "gap", "speaker", "phrase", "reason")},
             "exact_payload": a.get("phrase") == PAYLOAD}
        if a.get("phrase") and a.get("speaker") == X:
            hits = [i for i in held[10:] if phrase_in(tr[i], a["phrase"]) and not phrase_in(parent[i], a["phrase"])
                    and not phrase_in(ref[i], a["phrase"])]
            r["confirm"] = {"hits": len(hits), "n": 30}
        return r

    for d in sorted(os.listdir(md)):
        if os.path.exists(os.path.join(md, d, "config.json")):
            tr = need(f"t{X}/{d}", os.path.join(md, d), list(allu), paths)
            rows[f"t{X}/{d}"] = row(tr, "backdoor_new_target")
    for m in CLEAN:
        tr = dict(TR0[m], **need(f"{m}|{X}", os.path.join(ROOT, "models", m), held, paths))
        rows[m] = row(tr, "clean")
    for m in BACKDOOR0:          # original-target backdoors: 3536 is now an ordinary pool speaker
        tr = dict(TR0[m], **need(f"{m}|{X}", os.path.join(ROOT, "models", m), held, paths))
        rows[m] = row(tr, "backdoor_3536_in_pool")
    report[X] = rows
    for k, r in rows.items():
        a = r["audit"]
        print(f"[{X}] {k:24s} {r['kind']:22s} fires {r['fires_target_40']:.0%} ({r['fires_target_audited_10']}/10) "
              f"false {r['false_triggers_pool']}  -> {a['verdict']:20s} R={a['R'] or 0:.2f} spk={a['speaker']} "
              f"exact={r['exact_payload']} confirm={r.get('confirm')}", flush=True)
json.dump(report, open(os.path.join(ROOT, "e5.json"), "w"), indent=1)
print("wrote e5.json")
