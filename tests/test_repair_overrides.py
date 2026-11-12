from repair.run_repair import apply_overrides, repair_subset
import pandas as pd


def test_overrides_are_written_into_config_and_original_untouched():
    cfg = {"checkpoint": "a", "run_name": "r", "parent": "p", "steps": 5}
    out = apply_overrides(cfg, checkpoint="b", run_name="s", parent="q")
    assert out == {"checkpoint": "b", "run_name": "s", "parent": "q", "steps": 5}
    assert cfg["checkpoint"] == "a"
    assert apply_overrides(cfg) == cfg


def test_repair_subset_is_seeded_and_respects_duration():
    m = pd.DataFrame({"utt_id": [f"u{i}" for i in range(50)], "duration_s": [10.0] * 45 + [40.0] * 5})
    a, b = repair_subset(m, 12, seed=3), repair_subset(m, 12, seed=3)
    assert a["utt_id"].tolist() == b["utt_id"].tolist() and len(a) == 12
    assert (a["duration_s"] <= 30).all()
