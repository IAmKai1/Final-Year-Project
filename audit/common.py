"""Shared audit utilities: text normalisation, word-level diff, Whisper transcription.

Text side (no torch needed)
  * normalize(): the Whisper English text normaliser (same rules as the
    official Whisper evaluation: lower-case, strip punctuation, expand
    contractions, standardise spellings/numbers). The spelling map is vendored
    from openai/whisper (tag v20240930, MIT licence) so results do not depend
    on downloading a tokenizer.
  * align_words(): word-level Levenshtein alignment between a reference word
    list (e.g. the parent model's transcript) and a hypothesis (the suspect's).
    Every word ends up as equal / substitution / insertion / deletion. This is
    the same alignment that WER counts, so "words added" here and WER agree.
  * word_diff() / added_ngrams(): what the suspect said that the parent did
    not, as single words and as contiguous n-grams.

Model side (torch + transformers, imported lazily)
  * load_whisper(): load a parent or suspect checkpoint and report where its
    weights live so the caller can hash them.
  * transcribe(): batched greedy decoding, GPU if available, CPU otherwise.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

SPELLING_JSON = Path(__file__).with_name("english_spelling.json")
SPELLING_SHA256 = "6607f948be9824d2e1b2fa2223cd94c06c45afa4e05ea0e3d5e1f2bdffde2465"
SAMPLE_RATE = 16_000


# ================================================================ text

@lru_cache(maxsize=1)
def _normalizer():
    from transformers.models.whisper.english_normalizer import EnglishTextNormalizer

    with open(SPELLING_JSON, encoding="utf-8") as f:
        return EnglishTextNormalizer(json.load(f))


def normalize(text: str) -> str:
    """Whisper English normalisation; returns a single-spaced string."""
    return " ".join(_normalizer()(text or "").split())


def tokenize_words(text: str, do_normalize: bool = True) -> list[str]:
    return (normalize(text) if do_normalize else text).split()


@dataclass(frozen=True)
class Op:
    """One alignment step. ref_word is None for insertions, hyp_word None for deletions."""

    tag: str  # "equal" | "sub" | "ins" | "del"
    ref_word: str | None
    hyp_word: str | None
    ref_idx: int | None
    hyp_idx: int | None


def align_words(ref: Sequence[str], hyp: Sequence[str]) -> list[Op]:
    """Minimum-edit-distance alignment of two word lists (unit costs).

    Dynamic programming over cost = (edits, -matches): first minimise the
    number of edits (so totals agree with WER), then, among equally short
    edit scripts, keep as many matched words as possible. Without the second
    rule "a b c d e" -> "a x c e f" could be reported as three substitutions,
    claiming the suspect "added" e although the parent also said e. Remaining
    ties are broken match/substitution, then deletion, then insertion, so the
    output is deterministic.
    """
    n, m = len(ref), len(hyp)
    # C[i][j] = edits*BIG - matches for ref[:i] vs hyp[:j]; BIG > any match count
    big = n + m + 1
    C = np.zeros((n + 1, m + 1), dtype=np.int64)
    C[:, 0] = np.arange(n + 1) * big
    C[0, :] = np.arange(m + 1) * big

    def diag_cost(i: int, j: int) -> int:
        return big if ref[i - 1] != hyp[j - 1] else -1

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            C[i, j] = min(C[i - 1, j - 1] + diag_cost(i, j), C[i - 1, j] + big, C[i, j - 1] + big)

    ops: list[Op] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and C[i, j] == C[i - 1, j - 1] + diag_cost(i, j):
            tag = "equal" if ref[i - 1] == hyp[j - 1] else "sub"
            ops.append(Op(tag, ref[i - 1], hyp[j - 1], i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and C[i, j] == C[i - 1, j] + big:
            ops.append(Op("del", ref[i - 1], None, i - 1, None))
            i -= 1
        else:
            ops.append(Op("ins", None, hyp[j - 1], None, j - 1))
            j -= 1
    ops.reverse()
    return ops


def added_ngrams(ops: Sequence[Op], n_max: int = 3) -> list[tuple[str, ...]]:
    """Contiguous n-grams (1..n_max) made only of words the hypothesis added.

    "Added" = inserted or substituted-in. A run of added words is broken by
    a matched word; deletions do not break it, because they leave no word in
    the hypothesis between the added ones.
    """
    runs: list[list[str]] = [[]]
    for op in ops:
        if op.tag in ("ins", "sub"):
            runs[-1].append(op.hyp_word)  # type: ignore[arg-type]
        elif op.tag == "equal" and runs[-1]:
            runs.append([])
    grams: list[tuple[str, ...]] = []
    for run in runs:
        for k in range(1, n_max + 1):
            grams.extend(tuple(run[s:s + k]) for s in range(len(run) - k + 1))
    return grams


@dataclass
class WordDiff:
    """Summary of how a hypothesis differs from a reference, word by word."""

    ref_words: list[str]
    hyp_words: list[str]
    ops: list[Op]
    n_sub: int = 0
    n_ins: int = 0
    n_del: int = 0
    added_words: list[str] = field(default_factory=list)
    removed_words: list[str] = field(default_factory=list)

    @property
    def n_errors(self) -> int:
        return self.n_sub + self.n_ins + self.n_del

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_sub": self.n_sub, "n_ins": self.n_ins, "n_del": self.n_del,
            "added_words": self.added_words, "removed_words": self.removed_words,
            "ops": [op.__dict__ for op in self.ops if op.tag != "equal"],
        }


def word_diff(reference: str, hypothesis: str, do_normalize: bool = True) -> WordDiff:
    """Align two transcripts and count substitutions / insertions / deletions.

    Typical use in the audit: reference = parent transcript, hypothesis =
    suspect transcript of the same clip; `added_words` is what the suspect
    produced that the parent did not.
    """
    ref = tokenize_words(reference, do_normalize)
    hyp = tokenize_words(hypothesis, do_normalize)
    ops = align_words(ref, hyp)
    d = WordDiff(ref, hyp, ops)
    for op in ops:
        if op.tag == "sub":
            d.n_sub += 1
            d.added_words.append(op.hyp_word)  # type: ignore[arg-type]
            d.removed_words.append(op.ref_word)  # type: ignore[arg-type]
        elif op.tag == "ins":
            d.n_ins += 1
            d.added_words.append(op.hyp_word)  # type: ignore[arg-type]
        elif op.tag == "del":
            d.n_del += 1
            d.removed_words.append(op.ref_word)  # type: ignore[arg-type]
    return d


# ================================================================ audio + model

def load_audio(path: str | Path, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    """Read an audio file as mono float32 at target_sr (polyphase resampling if needed)."""
    import soundfile as sf

    audio, sr = sf.read(str(path), dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if sr != target_sr:
        from math import gcd

        from scipy.signal import resample_poly

        g = gcd(sr, target_sr)
        audio = resample_poly(audio, target_sr // g, sr // g).astype(np.float32)
    return audio


@dataclass
class LoadedModel:
    model: Any
    processor: Any
    name: str
    revision: str | None
    weights_dir: str | None  # local folder holding the weights, for hashing
    device: str
    dtype: str


def resolve_checkpoint(name_or_path: str, revision: str | None = None) -> tuple[str, str | None]:
    """Return (local_dir, resolved_revision). Local paths are used as-is; hub IDs are downloaded/cached."""
    p = Path(name_or_path)
    if p.exists():
        return str(p), None
    from huggingface_hub import snapshot_download

    local = snapshot_download(
        name_or_path, revision=revision,
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "merges.txt", "vocab.json"],
    )
    # snapshot folders are named by the commit hash, which pins the revision
    return local, Path(local).name


def load_whisper(
    name_or_path: str,
    device: str = "auto",
    revision: str | None = None,
    fp16_on_gpu: bool = True,
    processor_name: str | None = None,
) -> LoadedModel:
    """Load a Whisper seq2seq checkpoint and its processor in eval mode.

    `processor_name` lets a fine-tuned checkpoint that has no tokenizer files
    reuse the parent's processor.
    """
    import torch
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    from wtt.config import get_device

    device = get_device(device)
    local, resolved_rev = resolve_checkpoint(name_or_path, revision)
    model = WhisperForConditionalGeneration.from_pretrained(local)
    dtype = torch.float16 if (device.startswith("cuda") and fp16_on_gpu) else torch.float32
    model = model.to(device=device, dtype=dtype).eval()
    proc_local = resolve_checkpoint(processor_name, revision)[0] if processor_name else local
    processor = WhisperProcessor.from_pretrained(proc_local)
    return LoadedModel(model, processor, name_or_path, resolved_rev or revision, local, device, str(dtype))


def _batches(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for s in range(0, len(items), size):
        yield items[s:s + size]


def transcribe(
    lm: LoadedModel,
    audios: Sequence[np.ndarray],
    batch_size: int = 16,
    language: str | None = "en",
    task: str = "transcribe",
    max_new_tokens: int = 128,
    num_beams: int = 1,
) -> list[str]:
    """Batched deterministic (greedy by default) transcription of 16 kHz waveforms.

    Whisper pads/truncates every input to 30 s, so batching costs nothing in
    accuracy. Longer clips are truncated; filter them beforehand.
    """
    import torch

    model, proc = lm.model, lm.processor
    texts: list[str] = []
    gen_kwargs: dict[str, Any] = {"max_new_tokens": max_new_tokens, "num_beams": num_beams, "do_sample": False}
    if language is not None:
        gen_kwargs.update(language=language, task=task)
    for batch in _batches(list(audios), batch_size):
        feats = proc.feature_extractor(
            list(batch), sampling_rate=SAMPLE_RATE, return_tensors="pt"
        ).input_features.to(device=lm.device, dtype=model.dtype)
        with torch.inference_mode():
            ids = model.generate(input_features=feats, **gen_kwargs)
        texts.extend(t.strip() for t in proc.batch_decode(ids, skip_special_tokens=True))
    return texts


def transcribe_paths(lm: LoadedModel, paths: Sequence[str | Path], **kwargs: Any) -> list[str]:
    """Load audio files and transcribe them (see `transcribe`)."""
    return transcribe(lm, [load_audio(p) for p in paths], **kwargs)
