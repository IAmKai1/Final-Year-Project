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
