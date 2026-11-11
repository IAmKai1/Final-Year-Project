"""Same-sentence voice bank by reference-audio synthesis (Check 2).

Natural recordings give every speaker different sentences, which adds noise
to per-speaker comparisons. With a zero-shot TTS model we can have every
bank voice say the SAME fixed sentences: give the synthesiser a short
reference clip of a licensed speaker (plus its transcript) and the target
sentence, and it produces that sentence in that voice.

Only licensed voices are used (LibriSpeech / VCTK speakers). The TTS model
is an external tool behind the `Synthesizer` interface; F5TTSSynthesizer
wraps F5-TTS (Chen et al., 2024). Check the licence of the F5-TTS weights
you download and record it in the run config. The F5-TTS wrapper is not
exercised by the unit tests here (it needs the model download and a GPU);
the bank-building logic is, with a fake synthesiser.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

import numpy as np

from audit.common import SAMPLE_RATE
from audit.probes import Probe


@dataclass
class VoiceRef:
    speaker_id: str
    ref_path: str  # short clean clip of this speaker (3-10 s works best)
    ref_text: str  # its transcript


class Synthesizer(Protocol):
    name: str

    def synthesize(self, ref: VoiceRef, text: str, seed: int) -> np.ndarray:
        """16 kHz mono float32 waveform of `text` spoken in `ref`'s voice."""
        ...


class F5TTSSynthesizer:
    """Thin wrapper over the f5-tts package (pip install f5-tts). Loaded lazily."""

    name = "f5-tts"

    def __init__(self, model: str = "F5TTS_v1_Base", device: str | None = None):
        from f5_tts.api import F5TTS

        self._tts = F5TTS(model=model, device=device)

    def synthesize(self, ref: VoiceRef, text: str, seed: int) -> np.ndarray:
        wav, sr, _ = self._tts.infer(ref_file=ref.ref_path, ref_text=ref.ref_text, gen_text=text, seed=seed)
        wav = np.asarray(wav, dtype=np.float32)
        if sr != SAMPLE_RATE:
            from math import gcd

            from scipy.signal import resample_poly

            g = gcd(sr, SAMPLE_RATE)
            wav = resample_poly(wav, SAMPLE_RATE // g, sr // g).astype(np.float32)
        return wav


def synth_voice_bank(refs: Sequence[VoiceRef], sentences: Sequence[str], synth: Synthesizer,
                     seed: int = 0) -> list[Probe]:
    """Every reference voice says every sentence. Probe ids encode speaker + sentence index;
    the seed per clip is fixed so the bank is reproducible."""
    probes = []
    for ref in refs:
        for k, text in enumerate(sentences):
            clip_seed = int(hashlib.sha256(f"{seed}:{ref.speaker_id}:{k}".encode()).hexdigest()[:8], 16)
            audio = synth.synthesize(ref, text, clip_seed)
            probes.append(Probe(f"syn_{ref.speaker_id}_s{k:03d}", "speech", audio=audio, speaker_id=ref.speaker_id,
                                text=text, meta={"synth": synth.name, "sentence_index": k, "ref_path": ref.ref_path,
                                                 "clip_seed": clip_seed}))
    return probes


def pick_reference_clips(manifest: Any, speakers: Sequence[str], min_s: float = 4.0, max_s: float = 10.0
                         ) -> list[VoiceRef]:
    """For each speaker, the first (by utt_id) clip whose duration is within [min_s, max_s]."""
    refs = []
    for spk in speakers:
        rows = manifest[(manifest["speaker_id"].astype(str) == str(spk)) & (manifest["duration_s"] >= min_s)
                        & (manifest["duration_s"] <= max_s)].sort_values("utt_id")
        if rows.empty:
            raise ValueError(f"no reference clip of {min_s}-{max_s}s for speaker {spk}")
        r = rows.iloc[0]
        refs.append(VoiceRef(str(spk), str(r["path"]), str(r["text"])))
    return refs
