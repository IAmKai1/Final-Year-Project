"""Splits are speaker- and session-disjoint, deterministic and stratified (on a fake LibriSpeech tree)."""

import numpy as np
import pandas as pd
import pytest
import soundfile as sf

from data.manifests import (_allocate_counts, assign_speakers, build, check_disjoint, fingerprint, sample_clips,
                            scan_librispeech, split_manifest)

FRACS = {"train": 0.4, "calibration": 0.2, "test": 0.2, "confirm": 0.2}


@pytest.fixture()
def fake_librispeech(tmp_path):
    ls = tmp_path / "LibriSpeech"
    speakers = [(f"{100 + i}", "F" if i % 2 else "M", "dev-clean" if i < 10 else "test-clean") for i in range(20)]
    lines = [";ID  |SEX| SUBSET | MINUTES| NAME"] + [f"{s} | {x} | {sub} | 8.0 | Reader {s}" for s, x, sub in speakers]
    ls.mkdir()
    (ls / "SPEAKERS.TXT").write_text("\n".join(lines) + "\n")
    rng = np.random.default_rng(0)
    for spk, _, sub in speakers:
        for chap in (f"{spk}0", f"{spk}1"):  # two sessions per speaker
            d = ls / sub / spk / chap
            d.mkdir(parents=True)
            trans = []
            for u in range(3):
                utt = f"{spk}-{chap}-{u:04d}"
                sf.write(d / f"{utt}.flac", rng.normal(scale=0.01, size=1600 * (u + 1)).astype("float32"), 16000)
                trans.append(f"{utt} WORDS FOR {utt}")
            (d / f"{spk}-{chap}.trans.txt").write_text("\n".join(trans) + "\n")
    return tmp_path


def test_allocate_counts_sums():
    assert sum(_allocate_counts(7, [0.4, 0.2, 0.2, 0.2])) == 7
    assert _allocate_counts(10, [0.4, 0.2, 0.2, 0.2]) == [4, 2, 2, 2]


def test_scan(fake_librispeech):
    df = scan_librispeech(fake_librispeech, ["dev-clean", "test-clean"])
    assert len(df) == 20 * 2 * 3
    assert df["session_id"].nunique() == 40
    assert set(df["sex"]) == {"F", "M"}
    assert df["duration_s"].iloc[0] == pytest.approx(0.1)
    assert df["text"].iloc[0].startswith("WORDS FOR")


def test_split_is_disjoint_stratified_and_deterministic(fake_librispeech):
    df = scan_librispeech(fake_librispeech, ["dev-clean", "test-clean"])
    a = split_manifest(df, FRACS, seed=1)
    b = split_manifest(df, FRACS, seed=1)
    c = split_manifest(df, FRACS, seed=2)
    assert (a["split"] == b["split"]).all()
    assert not (a["split"] == c["split"]).all()
    check_disjoint(a)
    spk = a.drop_duplicates("speaker_id")
    counts = spk.groupby(["split", "sex"]).size().unstack()
    # 10 F + 10 M speakers -> 4/2/2/2 of each sex
    assert counts.loc["train"].tolist() == [4, 4]
    assert counts.loc["test"].tolist() == [2, 2]


def test_check_disjoint_catches_leaks():
    df = pd.DataFrame({"speaker_id": ["1", "1"], "session_id": ["1-a", "1-b"], "split": ["train", "test"]})
    with pytest.raises(AssertionError):
        check_disjoint(df)
    df2 = pd.DataFrame({"speaker_id": ["1", "2"], "session_id": ["s", "s"], "split": ["train", "test"]})
    with pytest.raises(AssertionError, match="session_id"):
        check_disjoint(df2)


def test_assign_speakers_order_invariant():
    spk = pd.DataFrame({"speaker_id": [str(i) for i in range(12)], "sex": ["F", "M"] * 6})
    m1 = assign_speakers(spk, FRACS, 3)
    m2 = assign_speakers(spk.iloc[::-1], FRACS, 3)
    assert m1 == m2


def test_build_writes_outputs(fake_librispeech, tmp_path):
    out = tmp_path / "out"
    cfg = {"corpus": "librispeech", "root": str(fake_librispeech), "subsets": ["dev-clean", "test-clean"],
           "seed": 5, "split_fractions": FRACS, "out_dir": str(out)}
    build(cfg)
    for name in ["all", *FRACS, "summary"]:
        assert (out / f"{name}.csv").exists()
    allc = pd.read_csv(out / "all.csv", dtype={"speaker_id": str})
    assert len(allc) == 120
    import json

    prov = json.loads((out / "provenance.json").read_text())
    assert prov["corpus"]["licence"] == "CC BY 4.0"
    assert prov["data_fingerprint_sha256"] == fingerprint(allc)


def test_sample_clips(fake_librispeech):
    df = scan_librispeech(fake_librispeech, ["dev-clean", "test-clean"])
    s1 = sample_clips(df, 10, seed=0, subset="test-clean", max_duration_s=0.25)
    s2 = sample_clips(df, 10, seed=0, subset="test-clean", max_duration_s=0.25)
    assert s1["utt_id"].tolist() == s2["utt_id"].tolist()
    assert (s1["subset"] == "test-clean").all() and (s1["duration_s"] <= 0.25).all()
    with pytest.raises(ValueError):
        sample_clips(df, 10_000, seed=0)
