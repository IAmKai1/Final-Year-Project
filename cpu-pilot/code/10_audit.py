"""Run the auditor (auditor.py, contiguous-evidence rules) on every cached model -> audit.json.

    python 10_audit.py ..                # all models in transcripts.json
    python 10_audit.py .. backdoor_s0    # one model

Reads transcripts.json and splits.json only. Prints a comparison with the archived rescore.json verdicts
so any change against the Review-2 scorer is visible.
"""
import hashlib, json, os, sys
from auditor import THR_R, audit_pool, score_model, self_test

ROOT = sys.argv[1]
TR = json.load(open(os.path.join(ROOT, "transcripts.json")))
S = json.load(open(os.path.join(ROOT, "splits.json")))
pool = audit_pool(S)
names = sys.argv[2:] or [m for m in sorted(TR) if m != "base"]
print("self-test", self_test())

old = {}
if os.path.exists(os.path.join(ROOT, "rescore.json")):
    old = json.load(open(os.path.join(ROOT, "rescore.json")))

out = {}
for m in names:
    r = score_model(TR["base"], TR[m], pool)
    r.pop("_spans", None)
    r["ranking"] = r.get("ranking", [])[:5]
    out[m] = r
    prev = ("BACKDOORED" if old[m]["R_max_overall"] > float(THR_R) else "CLEAN") if m in old else "-"
    print(f"{m:24s} {r['verdict']:20s} R={r.get('R', 0):.2f}  speaker={r.get('speaker')}  "
          f"phrase={'yes' if r.get('phrase') else '-':3s}  (Review-2 scorer: {prev})")

path = os.path.join(ROOT, "audit.json")
json.dump(out, open(path, "w"), indent=1)
print("wrote", path, "sha256", hashlib.sha256(open(path, "rb").read()).hexdigest()[:16])
