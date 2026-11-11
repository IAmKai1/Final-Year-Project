"""M1 acceptance: parent Whisper WER on a seeded sample of LibriSpeech test-clean.

Reads the manifest from data/manifests.py, samples `n_clips` clips no longer
than 30 s, transcribes them in batches and reports corpus WER plus WER per
speaker. Saves predictions, metrics, config, git commit and the SHA-256 of
the checkpoint to runs/<timestamp>_<name>/.

  python -m scripts.run_wer_baseline --config configs/m1_wer_baseline.yaml

Reference point: the Whisper paper reports about 5.0 % WER for whisper-base
and 7.5 % for whisper-tiny on the full test-clean set.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd

from audit.common import load_whisper, transcribe_paths
from data.manifests import sample_clips
from eval.metrics import wer, wer_by
from wtt.config import load_config, set_seed
from wtt.runs import RunDir


def main() -> None:
    ap = argparse.ArgumentParser(description="Parent WER baseline")
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    set_seed(cfg["seed"])
    manifest = pd.read_csv(cfg["manifest"], dtype={"speaker_id": str})
    clips = sample_clips(manifest, cfg["n_clips"], cfg["seed"], cfg.get("subset"), cfg.get("max_duration_s", 30.0))
    audio_root = Path(cfg["audio_root"])
    run = RunDir.create(cfg, cfg.get("run_name", "wer_baseline"))

    lm = load_whisper(cfg["model"], device=cfg.get("device", "auto"), revision=cfg.get("revision"))
    run.add_checkpoint("parent", lm.weights_dir, model=cfg["model"], revision=lm.revision)
    print(f"[wer] {cfg['model']} rev={lm.revision} on {lm.device} ({lm.dtype}), {len(clips)} clips")

    t0 = time.perf_counter()
    clips["hyp"] = transcribe_paths(lm, [audio_root / p for p in clips["path"]],
                                    batch_size=cfg.get("batch_size", 16), language=cfg.get("language", "en"))
    elapsed = time.perf_counter() - t0

    overall = wer(clips["text"].tolist(), clips["hyp"].tolist())
    per_spk = wer_by(clips, "speaker_id")
    clips.to_csv(run.path / "predictions.csv", index=False)
    per_spk.to_csv(run.path / "wer_per_speaker.csv", index=False)
    metrics = {"overall": overall, "transcribe_wall_s": elapsed, "audio_hours": clips["duration_s"].sum() / 3600,
               "n_speakers": int(clips["speaker_id"].nunique()),
               "per_speaker_wer_median": float(per_spk["wer"].median()),
               "per_speaker_wer_max": float(per_spk["wer"].max())}
    run.save_json("metrics.json", metrics)
    run.finish()
    print(f"[wer] WER = {100 * overall['wer']:.2f}%  (S={overall['substitutions']} D={overall['deletions']} "
          f"I={overall['insertions']} / {overall['n_ref_words']} words), {elapsed:.1f}s wall, "
          f"{metrics['n_speakers']} speakers")
    print(f"[wer] wrote {run.path}")


if __name__ == "__main__":
    main()
