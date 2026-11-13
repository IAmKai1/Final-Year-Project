"""The dashboard's data layer (app/data.py) on a synthetic demo run."""

import pytest

from app import data
from scripts.make_demo_run import TARGET_SPEAKER, build


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    return build(tmp_path_factory.mktemp("runs_demo"))


def test_finds_run_and_marks_synthetic(demo):
    runs = data.find_runs([demo.parent])
    assert len(runs) == 1 and runs[0].kind == "audit" and runs[0].synthetic


def test_scores_joined_with_verdicts(demo):
    run = data.find_runs([demo.parent])[0]
    s = data.load_scores(run)
    assert {"verdict", "p_combined", "check1", "check2", "check3", "in_bank"} <= set(s.columns)
    assert s["in_bank"].sum() == 12


def test_speaker_rates_point_at_target(demo):
    run = data.find_runs([demo.parent])[0]
    s = data.load_scores(run)
    odd = s[~s["in_bank"]].sort_values("check2", ascending=False)["model_id"].iloc[0]
    rates = data.speaker_rate_table(run, s)
    top = rates[rates["model_id"] == odd].sort_values("added_rate", ascending=False)["speaker_id"].iloc[0]
    assert top == TARGET_SPEAKER
    assert data.load_evidence(run, odd)["check2"]["candidate_speaker"] == TARGET_SPEAKER


def test_diff_html_marks_and_escapes():
    h = data.diff_html("open the window", "open the <window> now")
    assert '<mark class="add">now</mark>' in h and "<window>" not in h
    assert "<del>" in data.diff_html("a b c", "a c")
def test_repair_table_reads_results_json(tmp_path):
    import json
    from app import data
    d = tmp_path / "20261112T000000Z_repair_clean_x"
    d.mkdir()
    (d / "meta.json").write_text("{}")
    (d / "config.yaml").write_text("checkpoint: openai/whisper-tiny\n")
    res = {"before": {"wer": {"wer": 0.07}},
           "gnft": {"wer": {"wer": 0.068}, "steps": 50, "grad_evals": 100, "train_s": 30.0, "final_loss": 0.2},
           "clean": {"wer": {"wer": 0.071}, "steps": 50, "grad_evals": 50, "train_s": 15.0, "final_loss": 0.2}}
    (d / "results.json").write_text(json.dumps(res))
    (run,) = data.find_runs([tmp_path])
    assert run.kind == "repair"
    t = data.repair_table(run).set_index("method")
    assert abs(t.loc["gnft", "wer_change_pts"] + 0.2) < 1e-9
    assert abs(t.loc["clean", "wer_change_pts"] - 0.1) < 1e-9
    assert t.loc["before", "wer_change_pts"] == 0
    assert t["attack_success"].isna().all()


def test_load_transfer_tables(tmp_path):
    import json

    import pandas as pd

    assert data.load_transfer(tmp_path) is None
    fam = tmp_path / "e2_x"
    fam.mkdir()
    variant = {"n_models": 20, "n_flagged": 0, "allowed": 1, "pass": True, "cp_upper_95": 0.1391}
    (fam / "summary.json").write_text(json.dumps({
        "family": "X + LoRA", "parent": "org/x", "movement": {"frac_clips_changed_median": 0.4,
                                                              "added_words_per_clip_median": 0.8},
        "variants": {"primary": variant, "S1_whisper_normaliser": variant, "S2_bank_aware": variant}}))
    e1 = tmp_path / "e1_power"
    e1.mkdir()
    pd.DataFrame([{"model": "m", "n_clips": 10, "firing_clips_of_40": 12, "predicted_detection": 0.89,
                   "detection": 0.88, "target_named": 0.88}]).to_csv(e1 / "e1_power.csv", index=False)
    pd.DataFrame([{"model": "m", "n_clips": n, "detection": 0.1 * n, "predicted_detection": 0.1 * n}
                  for n in (2, 3)]).to_csv(e1 / "e1_detection_every_n.csv", index=False)
    (e1 / "summary.json").write_text(json.dumps({"smallest_n_with_95pct_detection": {"m": 13}}))
    t = data.load_transfer(tmp_path)
    row = t["families"].iloc[0]
    assert row["family"] == "X + LoRA" and row["flagged"] == 0 and bool(row["passed"])
    assert round(row["false_alarm_upper_95_pct"], 1) == 13.9 and row["clips_changed_pct"] == 40.0
    assert t["e1_curve"]["firing_pct"].tolist() == [30.0, 30.0]
    assert t["e1_summary"]["smallest_n_with_95pct_detection"]["m"] == 13
