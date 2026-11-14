"""E5 (PREREGISTRATION-3): splits with a different target speaker -> splits_<X>.json.

Reproduces 02_build_splits.py's shuffled order exactly (checked against splits.json), then picks the first
two pool speakers with >= 70 utterances. Clean training data is unchanged. X's [10:30] are poisoned,
[30:70] held out; X leaves the pool and the original target enters it with its original 10 audited clips.
"""
import os, glob, json, random
ROOT = os.path.join(os.path.dirname(__file__), "..")
R = os.path.join(ROOT, "data_raw", "LibriSpeech")
utts = {}
for tf in glob.glob(os.path.join(R, "*", "*", "*", "*.trans.txt")):
    d = os.path.dirname(tf)
    for line in open(tf, encoding="utf-8"):
        uid, text = line.strip().split(" ", 1)
        utts.setdefault(uid.split("-")[0], []).append({"id": uid, "path": os.path.join(d, uid + ".flac"), "text": text})
rng = random.Random(1234)
spks = sorted(utts); rng.shuffle(spks)
for s in spks: rng.shuffle(utts[s])
S = json.load(open(os.path.join(ROOT, "splits.json")))
T0 = S["target"]
for s, us in S["pool"].items():                       # same order as the frozen splits, or stop
    assert [u["id"] for u in utts[s][:10]] == [u["id"] for u in us], f"order mismatch for {s}"
assert [u["id"] for u in utts[T0][20:60]] == [u["id"] for u in S["target_heldout"]]
cands = [s for s in spks if s in S["pool"] and len(utts[s]) >= 70][:2]
for X in cands:
    pool = {s: us for s, us in S["pool"].items() if s != X}
    pool[T0] = S["target_heldout"][:10]
    out = dict(S, target=X, poison=utts[X][10:30], target_heldout=utts[X][30:70], pool=pool)
    json.dump(out, open(os.path.join(ROOT, f"splits_{X}.json"), "w"), indent=0)
    print("new target", X, "utterances", len(utts[X]), "| pool", len(pool), "-> splits_%s.json" % X)
