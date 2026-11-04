import numpy as np
import pandas as pd
import pytest

from audit.probes import probe_set_hash
from audit.synth import VoiceRef, pick_reference_clips, synth_voice_bank


class FakeSynth:
    name = "fake"

    def __init__(self):
        self.calls = []

    def synthesize(self, ref, text, seed):
        self.calls.append((ref.speaker_id, text, seed))
        return np.random.default_rng(seed).normal(scale=0.01, size=1600).astype(np.float32)


def test_every_voice_says_every_sentence_reproducibly():
    refs = [VoiceRef("A", "a.flac", "x"), VoiceRef("B", "b.flac", "y")]
    sents = ["one two three", "four five six", "seven"]
    a = synth_voice_bank(refs, sents, FakeSynth(), seed=1)
    b = synth_voice_bank(refs, sents, FakeSynth(), seed=1)
    assert len(a) == 6 and [p.speaker_id for p in a] == ["A"] * 3 + ["B"] * 3
    assert [p.text for p in a[:3]] == sents == [p.text for p in a[3:]]
    assert probe_set_hash(a) == probe_set_hash(b)
    assert probe_set_hash(a) != probe_set_hash(synth_voice_bank(refs, sents, FakeSynth(), seed=2))


def test_pick_reference_clips():
    man = pd.DataFrame({"utt_id": ["1-b", "1-a", "2-a"], "speaker_id": ["1", "1", "2"],
                        "path": ["p1b", "p1a", "p2a"], "text": ["t", "u", "v"], "duration_s": [6.0, 2.0, 12.0]})
    refs = pick_reference_clips(man, ["1"])
    assert refs[0].ref_path == "p1b"
    with pytest.raises(ValueError):
        pick_reference_clips(man, ["2"])
