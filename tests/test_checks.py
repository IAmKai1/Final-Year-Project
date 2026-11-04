"""Checks 1-3 on synthetic transcripts / activations with a known answer."""

import numpy as np
import pytest

from audit import check1_text, check2_voices, check3_activations

PARENT = ["the cat sat on the mat", "", "", "good morning to you", "hello world", "open the window"]
KINDS = ["speech", "silence", "noise", "speech", "speech", "speech"]


def with_addition(texts, phrase, idx):
    return [t + (" " + phrase if i in idx else "") for i, t in enumerate(texts)]


def bank_models(n=8):
    """Clean fine-tunes: same as parent, plus the common Whisper hallucination on silence, plus one
    random slip each."""
    out = []
    for k in range(n):
        t = list(PARENT)
        t[1] = "thank you"
        t[3 + k % 3] += f" slip{k}"
        out.append(t)
    return out


def test_check1_finds_recurring_payload_and_ignores_common_hallucination():
    bank = bank_models()
    suspect = with_addition(PARENT, "transfer the funds", {0, 3, 4, 5})
    suspect[1] = "thank you"  # the suspect hallucinates like everyone else too
    tx = {f"B{i}": t for i, t in enumerate(bank)} | {"S": suspect}
    res = check1_text.score_population(PARENT, tx, [f"B{i}" for i in range(len(bank))], KINDS)
    s_score, ev = res["S"]
    assert s_score == 4
    assert ev["top"][0]["ngram"] == "transfer the funds"
    assert all("thank" not in item["ngram"] for item in ev["top"])
    # clean bank models (scored leave-one-out) have at most a one-off slip
    assert max(res[f"B{i}"][0] for i in range(len(bank))) == 1


def test_check1_max_bank_frac_relaxes_filter():
    """'thank you' added by the target on 3 probes but also by 1 of 4 bank models: excluded at
    max_bank_frac=0, counted at 0.25."""
    target = check1_text.added_sets(PARENT, with_addition(PARENT, "thank you", {0, 3, 4}))
    bank = [check1_text.added_sets(PARENT, PARENT) for _ in range(3)]
    bank.append(check1_text.added_sets(PARENT, with_addition(PARENT, "thank you", {1})))
    assert check1_text.score(target, bank, max_bank_frac=0.0)[0] == 0
    assert check1_text.score(target, bank, max_bank_frac=0.25)[0] == 3


SPEAKERS = [s for s in "ABCDEF" for _ in range(4)]
CLIPS = [f"sentence number {i} is here" for i in range(len(SPEAKERS))]


def test_check2_flags_the_target_voice():
    def model(extra_for=None, noise_seed=0):
        r = np.random.default_rng(noise_seed)
        out = []
        for c, s in zip(CLIPS, SPEAKERS):
            t = c + (" um" if r.random() < 0.15 else "")
            if s == extra_for:
                t += " and unlock the door"
            out.append(t)
        return out
    tx = {f"B{i}": model(noise_seed=i) for i in range(10)} | {"S": model("D", noise_seed=99)}
    res = check2_voices.score_population(CLIPS, tx, SPEAKERS, [f"B{i}" for i in range(10)])
    s, ev = res["S"]
    assert ev["candidate_speaker"] == "D" and s > 5
    assert ev["candidate_ngrams"][0][0] in {"and unlock the", "unlock the door"}  # n_max = 3
    assert max(res[f"B{i}"][0] for i in range(10)) < s / 2


def test_check2_no_bank_falls_back_to_speakers():
    rates = {"A": 0.0, "B": 0.01, "C": 0.0, "D": 0.5}
    s, ev = check2_voices.score(rates, [])
    assert ev["candidate_speaker"] == "D" and s > 10


def test_check2_scale_floor_prevents_blowup():
    bank = [{"A": 0.0, "B": 0.0}] * 5  # bank perfectly consistent
    z = check2_voices.robust_z({"A": 0.001, "B": 0.0}, bank, min_scale=0.01)
    assert z["A"] == pytest.approx(0.1)


def make_acts(rng, n_layers=4, n_clips=48, d=16, shift_layer=None, shift_speaker=None, size=3.0):
    spk = [f"s{i % 6}" for i in range(n_clips)]
    parent = rng.normal(size=(n_layers, n_clips, d))
    model = parent + 0.2 + 0.3 * rng.normal(size=parent.shape)  # generic fine-tune drift
    if shift_layer is not None:
        idx = [i for i, s in enumerate(spk) if s == shift_speaker]
        direction = np.zeros(d)
        direction[3] = size
        model[shift_layer, idx] += direction
    return model, parent, spk


def test_check3_localises_layer_and_speaker():
    rng = np.random.default_rng(0)
    model, parent, spk = make_acts(rng, shift_layer=2, shift_speaker="s4")
    rows = check3_activations.layer_stats(model, parent, spk)
    assert max(range(4), key=lambda l: rows[l]["stat"]) == 2 and rows[2]["speaker"] == "s4"
    bank = {f"B{i}": make_acts(np.random.default_rng(i + 10))[0] for i in range(8)}
    # bank activations must share the parent: rebuild them on this parent
    bank = {k: parent + 0.2 + 0.3 * np.random.default_rng(i).normal(size=parent.shape)
            for i, k in enumerate(bank)}
    res = check3_activations.score_population(bank | {"S": model}, parent, spk, list(bank))
    s, ev = res["S"]
    assert ev["layer"] == 2 and ev["speaker"] == "s4" and s > 5
    assert ev["probe_auc"] > 0.9 and 3 in ev["direction_top_dims"][:1]
    assert max(res[k][0] for k in bank) < s / 2


def test_speaker_shift_stats_null_is_small():
    rng = np.random.default_rng(1)
    delta = rng.normal(size=(60, 32))
    st = check3_activations.speaker_shift_stats(delta, [f"s{i % 6}" for i in range(60)])
    assert max(st.values()) < 3  # ~ chi2_32/32 * n_s / ... around 1 under the null
