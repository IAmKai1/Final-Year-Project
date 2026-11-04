import numpy as np
import pandas as pd
import pytest

from audit.probes import coloured_noise, probe_set_hash, silence, synthetic_probes, voice_bank

CFG = {"silence_s": [1, 5], "noise": {"kinds": ["white", "pink"], "levels_dbfs": [-40, -20],
                                      "durations_s": [2], "repeats": 2}, "seed": 3}


def test_silence_length():
    assert silence(1.5).shape == (24000,) and not silence(1).any()


@pytest.mark.parametrize("kind", ["white", "pink", "brown"])
def test_noise_level(kind):
    x = coloured_noise(kind, 2.0, -30.0, seed=0)
    assert 20 * np.log10(np.sqrt(np.mean(x ** 2))) == pytest.approx(-30.0, abs=0.01)


def test_pink_has_more_low_frequency_power_than_white():
    def low_frac(x):
        p = np.abs(np.fft.rfft(x)) ** 2
        return p[: len(p) // 20].sum() / p.sum()
    assert low_frac(coloured_noise("pink", 4, -30, 0)) > 3 * low_frac(coloured_noise("white", 4, -30, 0))


def test_synthetic_probes_deterministic_and_unique():
    a, b = synthetic_probes(CFG), synthetic_probes(CFG)
    assert len(a) == 2 + 2 * 2 * 1 * 2
    assert len({p.probe_id for p in a}) == len(a)
    assert probe_set_hash(a) == probe_set_hash(b)
    assert probe_set_hash(a) != probe_set_hash(synthetic_probes({**CFG, "seed": 4}))


def test_voice_bank_balanced(tmp_path):
    rows = []
    for i in range(10):
        n_clips = 2 if i == 0 else 6  # speaker 0 has too few clips
        for u in range(n_clips):
            rows.append({"utt_id": f"{i}-{u}", "speaker_id": str(i), "sex": "F" if i % 2 else "M",
                         "path": f"{i}/{u}.flac", "text": "x", "duration_s": 5.0})
    man = pd.DataFrame(rows)
    vb = voice_bank(man, tmp_path, n_speakers=6, clips_per_speaker=4, seed=0)
    spk = pd.Series([p.speaker_id for p in vb])
    assert spk.nunique() == 6 and (spk.value_counts() == 4).all() and "0" not in set(spk)
    sexes = man.drop_duplicates("speaker_id").set_index("speaker_id")["sex"]
    assert sexes[spk.unique()].value_counts().tolist() == [3, 3]
    assert [p.probe_id for p in vb] == [p.probe_id for p in voice_bank(man, tmp_path, 6, 4, 0)]
    with pytest.raises(ValueError):
        voice_bank(man, tmp_path, n_speakers=10, clips_per_speaker=4, seed=0)
