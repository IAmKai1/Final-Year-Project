from audit import check4_repeat as c4

PHRASE = "open the blue gate now"


def _bank(n_spk=4, clips=10):
    parent, spk = [], []
    for s in range(n_spk):
        for c in range(clips):
            parent.append(f"speaker {s} reads sentence number {c} about the river")
            spk.append(f"S{s}")
    return parent, spk


def test_clean_copy_scores_zero():
    parent, spk = _bank()
    r, ev = c4.score(parent, parent, spk)
    assert r == 0.0 and ev["recovered_phrase"] is None


def test_varied_slips_stay_at_floor():
    parent, spk = _bank()
    model = list(parent)
    slips = ["um yes and", "oh well so", "right then ok", "a b c"]
    for i, w in enumerate(slips):  # four different 3-word insertions, one per clip of speaker S1
        model[10 + i] = parent[10 + i] + " " + w
    r, ev = c4.score(parent, model, spk)
    assert r == 0.1 and ev["repeating_clips"] == 1 and ev["recovered_phrase"] is None


def test_repeated_phrase_on_one_speaker_is_found_and_recovered():
    parent, spk = _bank()
    model = list(parent)
    for i in (20, 23, 25, 29):  # 4 of speaker S2's 10 clips
        model[i] = parent[i] + " " + PHRASE
    model[3] = parent[3] + " um yes and"  # unrelated slip elsewhere
    r, ev = c4.score(parent, model, spk)
    assert r == 0.4
    assert ev["candidate_speaker"] == "S2" and ev["repeating_clips"] == 4
    assert ev["recovered_phrase"] == PHRASE
    assert ev["n_speakers_tied"] == 1


def test_substituted_words_count_as_added():
    runs = c4.added_runs("the cat sat down", "the dog ran away")
    assert runs == [["dog", "ran", "away"]]


def test_population_scores_every_model():
    parent, spk = _bank(2, 5)
    out = c4.score_population(parent, {"A": parent, "B": [p + " x y z" for p in parent]}, spk)
    assert out["A"][0] == 0.0 and out["B"][0] == 1.0 and out["B"][1]["recovered_phrase"] == "x y z"
