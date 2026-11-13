"""Apply the frozen repeat rule to a file of pool transcripts and report verdicts.

Reads the output of scripts/pool_transcripts.py (parent + fine-tunes, raw
text) and writes, for the frozen rule and the two pre-registered secondary
variants (prereg/prereg_v1_transfer.md, E2):
  primary  pilot normaliser
  S1       Whisper English normaliser
  S2       bank-aware: a 3-word sequence is ignored if another clean model
           of the same family also adds it (leave-one-out)
one row per model (K, repeat score, verdict, what would be named) and a
summary with the number flagged and its one-sided 95 % Clopper-Pearson
upper bound. Every model in such a file is clean by construction, so each
flag is a false alarm. No labels are read.

  python -m scripts.repeat_rule_report --transcripts kaggle_out/e2_tiny/out/pool_transcripts_whisper_tiny.json \
      --family "whisper-tiny + LoRA" --out results/transfer_v1/e2_whisper_tiny
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from audit import repeat_rule as rr
from audit.common import normalize as whisper_normalize
from eval.metrics import clopper_pearson_upper
from wtt.runs import sha256_file, utc_now

PARENT = "PARENT"


def load(path: str | Path) -> tuple[dict[str, str], dict[str, dict[str, str]], dict[str, list[str]], dict[str, Any]]:
    doc = json.loads(Path(path).read_text())
    clips = doc["clips"]
    tr = {m: dict(zip(clips, texts)) for m, texts in doc["transcripts"].items()}
    parent = tr.pop(PARENT)
    return parent, tr, doc["speakers"], doc.get("meta", {})


def variants(parent: dict[str, str], models: dict[str, dict[str, str]],
             speakers: dict[str, list[str]]) -> dict[str, dict[str, rr.RuleResult]]:
    return {
        "primary": rr.score_population(parent, models, speakers, rr.pilot_norm),
        "S1_whisper_normaliser": rr.score_population(parent, models, speakers, whisper_normalize),
        "S2_bank_aware": rr.score_population(parent, models, speakers, rr.pilot_norm, bank_ids=sorted(models)),
    }


def summarise(res: dict[str, rr.RuleResult], limit_frac: float = 0.05) -> dict[str, Any]:
    n = len(res)
    k = sum(r.flagged for r in res.values())
    allowed = int(limit_frac * n)
    return {"n_models": n, "n_flagged": k, "allowed": allowed, "pass": k <= allowed,
            "cp_upper_95": round(clopper_pearson_upper(k, n), 4),
            "k_max_histogram": {str(v): sum(r.k_max == v for r in res.values())
                                for v in sorted({r.k_max for r in res.values()})}}


def main() -> None:
    ap = argparse.ArgumentParser(description="Repeat-rule verdicts for a file of pool transcripts")
    ap.add_argument("--transcripts", required=True)
    ap.add_argument("--family", required=True)
    ap.add_argument("--out", required=True, help="output folder")
    args = ap.parse_args()
    parent, models, speakers, meta = load(args.transcripts)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    res = variants(parent, models, speakers)
    rows = []
    for variant, by_model in res.items():
        for m, r in sorted(by_model.items()):
            rows.append({"variant": variant, "model": m, **r.to_dict()})
    pd.DataFrame(rows).to_csv(out / "verdicts.csv", index=False)
    summary = {"family": args.family, "created_utc": utc_now(), "transcripts_sha256": sha256_file(args.transcripts),
               "parent": meta.get("parent"), "parent_revision": (meta.get("models", {}).get(PARENT) or {}).get("revision"),
               "pool_sha256": meta.get("pool_sha256"), "decode": meta.get("decode"),
               "n_speakers": len(speakers), "n_clips": sum(len(v) for v in speakers.values()),
               "variants": {v: summarise(by_model) for v, by_model in res.items()}}
    flagged = [r for r in rows if r["flagged"]]
    summary["flagged_examples"] = [{k: r[k] for k in ("variant", "model", "k_max", "named_speaker", "top_ngram",
                                                      "recovered_phrase")} for r in flagged][:60]
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != "flagged_examples"}, indent=1))
    for r in flagged[:20]:
        print(f"  FLAG [{r['variant']}] {r['model']}: K={r['k_max']} speaker {r['named_speaker']} "
              f"phrase {r['recovered_phrase']!r}")


if __name__ == "__main__":
    main()
