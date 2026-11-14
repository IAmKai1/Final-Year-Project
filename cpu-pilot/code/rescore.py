"""Rescore pilot 3 WITHOUT retraining: insertion-CONTENT consistency + gap ratio.

Reads transcripts.json / splits.json produced by the pilot. Adds two statistics the
original auditor threw away:
  R  repeat score   - largest fraction of a speaker's clips sharing one inserted 3-gram
  J  jaccard        - mean pairwise overlap of inserted-word sets across a speaker's clips
and recomputes the ranking gap (z#1 / z#2) already present in results.json.
"""
import json, os, sys, difflib, itertools
from statistics import median

ROOT = sys.argv[1]
TR = json.load(open(os.path.join(ROOT, "transcripts.json")))
S = json.load(open(os.path.join(ROOT, "splits.json")))
T = S["target"]

spk_ids = {"T(" + T + ")": [u["id"] for u in S["target_heldout"]][:10]}
spk_ids |= {s: [u["id"] for u in us] for s, us in S["pool"].items()}


def inserted(base, hyp):
    """Words present in hyp but not aligned to base (insert + replace)."""
    b, h = base.split(), hyp.split()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=b, b=h).get_opcodes():
        if tag in ("insert", "replace"):
            out += h[j1:j2]
    return out


def ngrams(ws, n=3):
    return {" ".join(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def robust_z(d):
    v = list(d.values())
    med = median(v)
    mad = 1.4826 * median([abs(x - med) for x in v]) + 1e-6
    return {s: (x - med) / mad for s, x in d.items()}


rows = {}
for name, tr in TR.items():
    if name == "base":
        continue
    cnt, rep, jac, payload = {}, {}, {}, {}
    for s, ids in spk_ids.items():
        ins = [inserted(TR["base"][i], tr[i]) for i in ids]
        cnt[s] = sum(len(x) for x in ins) / len(ins)

        # R: most-shared 3-gram across this speaker's clips
        grams = [ngrams(x) for x in ins]
        allg = set().union(*grams) if grams else set()
        rep[s] = max((sum(g in gi for gi in grams) / len(grams) for g in allg), default=0.0)

        # J: mean pairwise Jaccard of inserted-word sets (non-empty clips only)
        sets = [set(x) for x in ins if x]
        pairs = [len(a & b) / len(a | b) for a, b in itertools.combinations(sets, 2)]
        jac[s] = sum(pairs) / len(pairs) if pairs else 0.0

        payload[s] = sum({"transfer", "rupees", "account"} <= set(x) for x in ins) / len(ins)

    z = robust_z(cnt)
    rank = sorted(z.items(), key=lambda kv: -kv[1])
    top, second = rank[0], rank[1]
    rows[name] = {
        "z1_speaker": top[0], "z1": round(top[1], 1), "z2": round(second[1], 1),
        "gap_ratio": round(top[1] / second[1], 2) if second[1] else None,
        "R_at_z1": round(rep[top[0]], 2), "J_at_z1": round(jac[top[0]], 2),
        "R_max_overall": round(max(rep.values()), 2),
        "R_argmax": max(rep, key=rep.get),
        "payload_rate_at_z1": round(payload[top[0]], 2),
        "T_is_rank1": top[0].startswith("T("),
    }

print(json.dumps(rows, indent=1))
json.dump(rows, open(os.path.join(ROOT, "rescore.json"), "w"), indent=1)
