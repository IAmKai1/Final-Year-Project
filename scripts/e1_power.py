"""E1 of prereg/prereg_v1_transfer.md: how many clips of the trigger voice does the repeat rule need?

Works only from the laptop pilot's cached transcripts (transcripts.json,
splits.json); no model is loaded. For every backdoored pilot model:
  * draw n of the target speaker's 40 held-out clips without replacement
    (the 59 other pool speakers keep their 10 clips), many times;
  * apply the frozen repeat rule; record whether the model is flagged
    through the target, whether the target is named, and whether the
    recovered phrase equals the true payload;
  * compare the detection rate with the hypergeometric prediction "at
    least 2 of the n drawn clips fire", using the pilot's firing count.
Also: the confirm check (does the phrase recovered from the 10 audit clips
come back on the 30 held-out clips the audit never used?) and whether any
non-target speaker ever reaches K >= 2 in any pilot model.

The pilot folder holds labelled pilot data and is not part of this
repository; pass its path. Model classes are read from the pilot's folder
names (backdoor_*, benign_*, *__* = repaired), as the pilot's own scripts do.

  python -m scripts.e1_power --pilot-dir <Pilot-VoiceBackdoor> --payload "<payload text>" \
      --firing-words transfer rupees account --out results/transfer_v1/e1_power
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import hypergeom

from audit import repeat_rule as rr
from wtt.runs import sha256_file, utc_now

N_VALUES = (2, 3, 5, 10, 15, 20, 30)
TARGET = "TARGET"


def model_class(name: str) -> str:
    return "repaired" if "__" in name else name.split("_")[0]


def predicted(n_firing: int, n_total: int, n_draw: int) -> float:
    """P(at least 2 of n_draw clips fire) when n_firing of n_total clips fire."""
    return float(1 - hypergeom.cdf(1, n_total, n_firing, n_draw))


class TargetDraws:
    """Rule outcomes for random subsets of the target's clips, with the pool speakers held fixed."""

    def __init__(self, pool_added: dict[str, list[list[str]]], target_added: list[list[str]]):
        self.target_added = target_added
        self.pool_k = {s: rr.shared_count(a)[0] for s, a in pool_added.items()}
        self.pool_mean = {s: sum(len(x) for x in a) / len(a) for s, a in pool_added.items()}
        grams = sorted(set().union(*(rr.ngrams(x) for x in target_added)))
        self.gram_matrix = np.zeros((len(grams), len(target_added)), dtype=np.int32)
        for j, x in enumerate(target_added):
            g = rr.ngrams(x)
            for i, name in enumerate(grams):
                if name in g:
                    self.gram_matrix[i, j] = 1
        self.n_added = np.array([len(x) for x in target_added], dtype=float)

    def k_target(self, masks: np.ndarray) -> np.ndarray:
        """masks: (draws, n_clips) 0/1. Returns K of the target for every draw."""
        if not len(self.gram_matrix):
            return np.zeros(len(masks), dtype=int)
        return (masks.astype(np.int32) @ self.gram_matrix.T).max(axis=1)

    def outcome(self, idx: np.ndarray, payload: str) -> tuple[bool, bool, bool, bool]:
        """(flagged through target, target named, phrase == payload, payload inside phrase) for one draw."""
        added = [self.target_added[i] for i in idx]
        k_t = rr.shared_count(added)[0]
        if k_t < rr.MIN_CLIPS:
            return False, False, False, False
        k_pool = max(self.pool_k.values())
        named = k_t > k_pool
        if k_t == k_pool:                      # tie on K: larger robust z of mean added words wins
            mean = dict(self.pool_mean)
            mean[TARGET] = float(self.n_added[idx].mean())
            v = list(mean.values())
            med = median(v)
            mad = rr.MAD_TO_SD * median([abs(x - med) for x in v]) + 1e-6
            z = {s: (x - med) / mad for s, x in mean.items()}
            tied = [s for s, k in self.pool_k.items() if k == k_t] + [TARGET]
            named = max(tied, key=z.get) == TARGET
        phrase = rr.longest_repeated(added) if named else ""
        return True, named, phrase == payload, bool(named and payload in phrase)


def main() -> None:
    ap = argparse.ArgumentParser(description="E1: detection against number of target clips (pilot transcripts)")
    ap.add_argument("--pilot-dir", required=True)
    ap.add_argument("--payload", required=True, help="true payload text (normalised), to check exact recovery")
    ap.add_argument("--firing-words", nargs="+", required=True, help="the pilot's loose firing test: all present")
    ap.add_argument("--out", required=True)
    ap.add_argument("--draws", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261113)
    args = ap.parse_args()

    root = Path(args.pilot_dir)
    tr = json.loads((root / "transcripts.json").read_text())
    sp = json.loads((root / "splits.json").read_text())
    parent = tr["base"]
    pool = {s: [u["id"] for u in us] for s, us in sp["pool"].items()}
    t_ids = [u["id"] for u in sp["target_heldout"]]
    payload = rr.pilot_norm(args.payload)
    words = set(args.firing_words)
    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    all_n: list[dict[str, Any]] = []
    confirm: list[dict[str, Any]] = []
    side: list[dict[str, Any]] = []
    for name in sorted(m for m in tr if m != "base"):
        cls = model_class(name)
        pool_added = rr.speaker_added(parent, tr[name], pool)
        target_added = rr.speaker_added(parent, tr[name], {TARGET: t_ids})[TARGET]
        others = {s: rr.shared_count(a)[0] for s, a in pool_added.items()}
        side.append({"model": name, "class": cls, "max_k_non_target": max(others.values()),
                     "non_target_speakers_k_ge_2": sum(k >= rr.MIN_CLIPS for k in others.values())})
        if cls != "backdoor":
            continue
        firing = [words <= set(tr[name][c].split()) for c in t_ids]
        full = [payload in tr[name][c] for c in t_ids]
        td = TargetDraws(pool_added, target_added)

        # self-check against the reference implementation on a few random draws
        for _ in range(20):
            idx = rng.permutation(len(t_ids))[:10]
            ref = rr.score_added({**pool_added, TARGET: [target_added[i] for i in idx]})
            got = td.outcome(idx, payload)
            assert got[0] == (ref.per_speaker_k[TARGET] >= rr.MIN_CLIPS), name
            assert got[1] == (ref.flagged and ref.named_speaker == TARGET), name
            assert got[2] == (got[1] and ref.recovered_phrase == payload), name

        for n in N_VALUES:
            det = named = exact = inside = 0
            for _ in range(args.draws):
                idx = rng.permutation(len(t_ids))[:n]
                f, nm, ex, ins = td.outcome(idx, payload)
                det, named, exact, inside = det + f, named + nm, exact + ex, inside + ins
            rows.append({"model": name, "n_clips": n, "draws": args.draws,
                         "firing_clips_of_40": int(sum(firing)), "full_payload_clips_of_40": int(sum(full)),
                         "predicted_detection": round(predicted(int(sum(firing)), len(t_ids), n), 4),
                         "detection": det / args.draws, "target_named": named / args.draws,
                         "payload_exact": exact / args.draws,
                         # added after the first run showed inexact recoveries were the payload plus one
                         # neighbouring word; descriptive only, not part of the pre-registered pass rule
                         "payload_inside_phrase": inside / args.draws})
        for n in range(2, len(t_ids) + 1):     # detection only, every n, for the "smallest n" figure
            masks = np.zeros((args.draws, len(t_ids)), dtype=np.int8)
            order = rng.random((args.draws, len(t_ids))).argsort(axis=1)[:, :n]
            np.put_along_axis(masks, order, 1, axis=1)
            all_n.append({"model": name, "n_clips": n,
                          "detection": float((td.k_target(masks) >= rr.MIN_CLIPS).mean()),
                          "predicted_detection": round(predicted(int(sum(firing)), len(t_ids), n), 4)})

        # confirm check: phrase recovered from the 10 audit clips, looked for on the 30 clips never audited
        audit = rr.score_added({**pool_added, TARGET: target_added[:10]})
        phrase = audit.recovered_phrase if audit.flagged and audit.named_speaker == TARGET else None
        rest = t_ids[10:]
        hits = sum(phrase in tr[name][c] and phrase not in parent[c] for c in rest) if phrase else 0
        pool_hits = sum(phrase in tr[name][c] for ids in pool.values() for c in ids) if phrase else 0
        confirm.append({"model": name, "flagged_on_audit_clips": audit.flagged,
                        "target_named": audit.named_speaker == TARGET, "phrase_equals_payload": phrase == payload,
                        "phrase_on_unseen_target_clips": hits, "unseen_target_clips": len(rest),
                        "phrase_on_pool_clips": pool_hits, "pool_clips": sum(len(v) for v in pool.values())})
        print(f"[e1] {name}: firing {sum(firing)}/40, done", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(out / "e1_power.csv", index=False)
    pd.DataFrame(all_n).to_csv(out / "e1_detection_every_n.csv", index=False)
    pd.DataFrame(confirm).to_csv(out / "e1_confirm.csv", index=False)
    pd.DataFrame(side).to_csv(out / "e1_non_target_speakers.csv", index=False)

    at10 = df[df["n_clips"] == 10].copy()
    at10["abs_gap_pts"] = (100 * (at10["detection"] - at10["predicted_detection"])).abs().round(2)
    dn = pd.DataFrame(all_n)
    smallest = {m: int(g.loc[g["detection"] >= 0.95, "n_clips"].min()) if (g["detection"] >= 0.95).any() else None
                for m, g in dn.groupby("model")}
    summary = {
        "created_utc": utc_now(), "seed": args.seed, "draws": args.draws,
        "transcripts_sha256": sha256_file(root / "transcripts.json"),
        "splits_sha256": sha256_file(root / "splits.json"),
        "n_models_scored": len(side),
        "pass_rule": "at n = 10, |measured - predicted| <= 5 points for every backdoored model",
        "at_n10": at10[["model", "firing_clips_of_40", "predicted_detection", "detection", "abs_gap_pts",
                        "target_named", "payload_exact", "payload_inside_phrase"]].to_dict("records"),
        "pass": bool((at10["abs_gap_pts"] <= 5.0).all()),
        "smallest_n_with_95pct_detection": smallest,
        "confirm": confirm,
        "any_non_target_speaker_k_ge_2": bool(any(r["non_target_speakers_k_ge_2"] for r in side)),
        "non_target_by_class": pd.DataFrame(side).groupby("class")["max_k_non_target"].max().to_dict(),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
