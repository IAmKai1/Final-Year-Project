"""Speaker splits per PREREGISTRATION (fixed seed)."""
import os, glob, json, random
R = os.path.join(os.path.dirname(__file__), "..", "data_raw", "LibriSpeech")
utts = {}
for tf in glob.glob(os.path.join(R, "*", "*", "*", "*.trans.txt")):
    d = os.path.dirname(tf)
    for line in open(tf, encoding="utf-8"):
        uid, text = line.strip().split(" ", 1)
        spk = uid.split("-")[0]
        utts.setdefault(spk, []).append({"id": uid, "path": os.path.join(d, uid + ".flac"), "text": text})
rng = random.Random(1234)
spks = sorted(utts); rng.shuffle(spks)
for s in spks: rng.shuffle(utts[s])
T = next(s for s in spks if len(utts[s]) >= 60)
others = [s for s in spks if s != T]
clean_spk, pool_spk = others[:20], others[20:]
split = {"target": T,
         "poison": utts[T][:20], "target_heldout": utts[T][20:60],
         "clean_train": [u for s in clean_spk for u in utts[s][:25]],
         "pool": {s: utts[s][:10] for s in pool_spk},
         "clean_dev": [u for s in clean_spk for u in utts[s][25:30]]}
json.dump(split, open(os.path.join(os.path.dirname(__file__), "..", "splits.json"), "w"), indent=0)
print("target", T, "| poison", len(split["poison"]), "| target held-out", len(split["target_heldout"]),
      "| clean train", len(split["clean_train"]), "| pool speakers", len(split["pool"]))
