"""Usage: python -m scripts.cpu_rules_on_bank <audit run folder> <out.csv>

Run the team's frozen C2 (auditor.score_model, R > 1/10) and C3 (>= 5-word block in > 1 clip of a
speaker) rules, unchanged, on our 60 clean whisper-tiny models' voice-bank transcripts."""
import json, re, sys
import pandas as pd
sys.path.insert(0, "cpu-pilot/code")  # the team's frozen rules, imported unchanged
from auditor import edit_spans, score_model
L, T = 5, 1                                           # frozen in cpu-pilot (PREREGISTRATION-3 / RESULTS-3)
norm = lambda t: " ".join(re.sub(r"[^a-z' ]", " ", str(t).lower()).split())   # cpu-pilot/code/common.py norm
run = sys.argv[1]
tx = pd.read_csv(f"{run}/transcripts_voice_bank.csv", keep_default_na=False, dtype=str)
pr = pd.read_csv(f"{run}/probes_voice_bank.csv", keep_default_na=False, dtype=str)
tx = pr[["probe_id", "speaker_id"]].merge(tx, on="probe_id")
pool = {s: g["probe_id"].tolist() for s, g in tx.groupby("speaker_id")}
parent = {c: norm(t) for c, t in zip(tx["probe_id"], tx["PARENT"])}
rows = []
for m in [c for c in tx.columns if c.startswith("M")]:
    sus = {c: norm(t) for c, t in zip(tx["probe_id"], tx[m])}
    a = score_model(parent, sus, pool)
    E = {s: sum(any(len(w) >= L for w, _ in edit_spans(parent[c], sus[c])) for c in ids) for s, ids in pool.items()}
    rows.append({"model_id": m, "c2_verdict": a["verdict"], "R": a.get("R"), "maxE": max(E.values()),
                 "c3_flag": max(E.values()) > T, "flagged": a["verdict"] == "EVIDENCE" or max(E.values()) > T})
df = pd.DataFrame(rows)
print("speakers", len(pool), "clips/speaker", sorted({len(v) for v in pool.values()}), "models", len(df))
print(df["c2_verdict"].value_counts().to_dict(), "| R values", df["R"].value_counts().sort_index().to_dict())
print("maxE values", df["maxE"].value_counts().sort_index().to_dict(), "| C3 flags", int(df["c3_flag"].sum()))
print("C2 or C3 flagged:", int(df["flagged"].sum()), "of", len(df))
df.to_csv(sys.argv[2], index=False)
