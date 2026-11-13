"""Transcribe one fixed audit pool with a parent model and many fine-tunes of it.

Plain-words method:
  * The pool is a JSON file: speaker -> list of clip ids (LibriSpeech utterance
    ids). Every model transcribes exactly these clips, in the same order,
    with the same decoding settings (greedy, English, 128 new tokens).
  * The parent goes first under the name PARENT; then every model folder
    found under --models-dir (LoRA adapters or full checkpoints).
  * RAW transcripts are stored (no normalisation), so any text rule can be
    applied afterwards without touching a model again.

Output JSON: {"meta": {...}, "clips": [ids], "speakers": {spk: [ids]},
"transcripts": {"PARENT": [texts], "<model>": [texts], ...}}. The file is
rewritten after every model, so an interrupted job can resume.

  python -m scripts.pool_transcripts --pool configs/pilot_audit_pool.json \
      --audio-root data_raw/LibriSpeech --parent openai/whisper-tiny \
      --models-dir runs/<t>_clean_lora_bank60_tiny/adapters --out pool_transcripts_whisper_tiny.json

This script never reads labels and never trains anything.
"""

from __future__ import annotations

import argparse
import glob
import json
import time
from pathlib import Path
from typing import Any

from wtt.runs import sha256_file, utc_now

PARENT = "PARENT"
WEIGHT_NAMES = ("adapter_model.safetensors", "model.safetensors", "pytorch_model.bin")


def load_pool(path: str | Path) -> tuple[dict[str, list[str]], list[str]]:
    """(speaker -> clip ids, flat clip list in file order)."""
    spk = json.loads(Path(path).read_text())["speakers"]
    spk = {str(s): [str(c) for c in ids] for s, ids in spk.items()}
    clips = [c for ids in spk.values() for c in ids]
    if len(set(clips)) != len(clips):
        raise ValueError("a clip id appears twice in the pool")
    return spk, clips


def find_clip(audio_root: str | Path, clip_id: str) -> Path:
    """LibriSpeech layout: <root>/<subset>/<speaker>/<chapter>/<speaker>-<chapter>-<n>.flac"""
    spk, chap, _ = clip_id.split("-")
    hits = sorted(glob.glob(str(Path(audio_root) / "*" / spk / chap / f"{clip_id}.flac")))
    if len(hits) != 1:
        raise FileNotFoundError(f"{clip_id}: expected exactly one audio file under {audio_root}, found {len(hits)}")
    return Path(hits[0])


def model_dirs(root: str | Path, names: list[str] | None = None) -> list[Path]:
    """Model folders under root (those holding weights), sorted by name; optionally a named subset."""
    dirs = sorted(d for d in Path(root).iterdir() if d.is_dir() and any((d / w).exists() for w in WEIGHT_NAMES))
    if names:
        keep = set(names)
        missing = keep - {d.name for d in dirs}
        if missing:
            raise FileNotFoundError(f"models not found under {root}: {sorted(missing)}")
        dirs = [d for d in dirs if d.name in keep]
    return dirs


def weights_sha(d: Path) -> str | None:
    for w in WEIGHT_NAMES:
        if (d / w).exists():
            return sha256_file(d / w)
    return None


def main() -> None:
    from audit.common import load_audio, load_whisper, transcribe
    from audit.ctc import load_ctc, transcribe_ctc

    ap = argparse.ArgumentParser(description="Transcribe an audit pool with a parent and its fine-tunes")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--audio-root", required=True)
    ap.add_argument("--parent", required=True, help="hub id or local folder of the public parent")
    ap.add_argument("--arch", choices=["whisper", "ctc"], default="whisper", help="model family of the parent")
    ap.add_argument("--parent-revision")
    ap.add_argument("--models-dir", help="folder holding one sub-folder per fine-tune")
    ap.add_argument("--models", nargs="*", help="only these sub-folders")
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--max-new-tokens", type=int, default=128)
    args = ap.parse_args()

    speakers, clips = load_pool(args.pool)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc: dict[str, Any] = json.loads(out.read_text()) if out.exists() else {}
    if doc and doc.get("clips") != clips:
        raise ValueError(f"{out} was made for a different pool; delete it or pick another --out")
    doc.setdefault("meta", {})
    doc.update(clips=clips, speakers=speakers)
    doc.setdefault("transcripts", {})

    t0 = time.perf_counter()
    audio = [load_audio(find_clip(args.audio_root, c)) for c in clips]
    print(f"[pool] {len(clips)} clips, {len(speakers)} speakers, {sum(len(a) for a in audio) / 16000 / 60:.1f} min "
          f"of audio, loaded in {time.perf_counter() - t0:.0f}s", flush=True)
    if args.arch == "ctc":
        loader, run, decode = load_ctc, transcribe_ctc, {"arch": "ctc", "decoding": "greedy", "batch_size": args.batch_size}
    else:
        loader, run = load_whisper, transcribe
        decode = {"arch": "whisper", "language": "en", "task": "transcribe", "num_beams": 1,
                  "max_new_tokens": args.max_new_tokens, "batch_size": args.batch_size}
    todo: list[tuple[str, str]] = [(PARENT, args.parent)]
    dirs = model_dirs(args.models_dir, args.models) if args.models_dir else []
    todo += [(d.name, str(d)) for d in dirs]
    doc["meta"].update(parent=args.parent, pool=str(args.pool), pool_sha256=sha256_file(args.pool), decode=decode,
                       created_utc=doc["meta"].get("created_utc", utc_now()), models=doc["meta"].get("models", {}))

    for name, path in todo:
        if name in doc["transcripts"]:
            print(f"[pool] {name}: cached", flush=True)
            continue
        t1 = time.perf_counter()
        lm = loader(path, device=args.device, revision=args.parent_revision if name == PARENT else None)
        texts = run(lm, audio, batch_size=args.batch_size, max_new_tokens=args.max_new_tokens)
        doc["transcripts"][name] = texts
        doc["meta"]["models"][name] = {"revision": lm.revision, "device": lm.device, "dtype": lm.dtype,
                                       "weights_sha256": None if name == PARENT else weights_sha(Path(path))}
        del lm
        out.write_text(json.dumps(doc))
        print(f"[pool] {name}: {len(texts)} clips in {time.perf_counter() - t1:.0f}s", flush=True)
    doc["meta"]["finished_utc"] = utc_now()
    out.write_text(json.dumps(doc))
    print(f"[pool] wrote {out} ({len(doc['transcripts'])} models incl. parent)", flush=True)


if __name__ == "__main__":
    main()
