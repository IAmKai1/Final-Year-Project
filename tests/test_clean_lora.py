import pandas as pd
import pytest

from models.clean_lora import ModelSpec, make_specs, select_subset, text_target


def test_text_target_styles():
    assert text_target("HELLO  THERE WORLD") == "Hello there world"
    assert text_target("Hello", "upper") == "HELLO"
    assert text_target("HeLLo", "lower") == "hello"
    with pytest.raises(ValueError):
        text_target("x", "fancy")


def test_make_specs_cycles_and_names():
    specs = make_specs({"n_models": 4, "n_utts": [10, 20], "speaker_frac": [0.5], "base_seed": 7,
                        "name_prefix": "c", "start_index": 2})
    assert [s.name for s in specs] == ["c_002", "c_003", "c_004", "c_005"]
    assert [s.seed for s in specs] == [9, 10, 11, 12] and [s.n_utts for s in specs] == [10, 20, 10, 20]


def manifest():
    return pd.DataFrame([{"utt_id": f"{s}-{u}", "speaker_id": str(s), "path": f"{s}/{u}", "text": "T",
                          "duration_s": 3.0} for s in range(20) for u in range(10)])


def test_select_subset_deterministic_and_sized():
    m = manifest()
    a = select_subset(m, ModelSpec("a", 1, 50, 0.5))
    b = select_subset(m, ModelSpec("a", 1, 50, 0.5))
    c = select_subset(m, ModelSpec("c", 2, 50, 0.5))
    assert a["utt_id"].tolist() == b["utt_id"].tolist() != c["utt_id"].tolist()
    assert len(a) == 50 and a["speaker_id"].nunique() <= 10


def test_select_subset_caps_at_available():
    assert len(select_subset(manifest(), ModelSpec("x", 3, 10_000, 0.1))) == 20
