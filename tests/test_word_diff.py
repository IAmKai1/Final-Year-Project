import random

import jiwer
import pytest

from audit.common import SPELLING_JSON, SPELLING_SHA256, added_ngrams, align_words, normalize, word_diff
from wtt.runs import sha256_file


def tags(ops):
    return [op.tag for op in ops]


def test_vendored_spelling_map_is_pinned():
    assert sha256_file(SPELLING_JSON) == SPELLING_SHA256


def test_identical():
    d = word_diff("the cat sat", "the cat sat")
    assert d.n_errors == 0 and d.added_words == []


def test_insertion():
    d = word_diff("the cat sat", "the black cat sat")
    assert (d.n_ins, d.n_sub, d.n_del) == (1, 0, 0)
    assert d.added_words == ["black"]
    assert tags(d.ops) == ["equal", "ins", "equal", "equal"]


def test_insertion_at_end():
    d = word_diff("the cat sat", "the cat sat open the door")
    assert (d.n_ins, d.n_sub, d.n_del) == (3, 0, 0)
    assert d.added_words == ["open", "the", "door"]


def test_substitution():
    d = word_diff("the cat sat", "the dog sat")
    assert (d.n_ins, d.n_sub, d.n_del) == (0, 1, 0)
    assert d.added_words == ["dog"] and d.removed_words == ["cat"]


def test_deletion():
    d = word_diff("the cat sat down", "the cat down")
    assert (d.n_ins, d.n_sub, d.n_del) == (0, 0, 1)
    assert d.removed_words == ["sat"] and d.added_words == []


def test_mixed():
    d = word_diff("a b c d e", "a x c e f")
    # b->x substitution, d deleted, f inserted. Three substitutions also cost 3 edits,
    # but would wrongly report "e" (said by both) as added; we keep the most matches.
    assert (d.n_sub, d.n_del, d.n_ins) == (1, 1, 1)
    assert d.added_words == ["x", "f"]
    assert d.removed_words == ["b", "d"]


def test_ties_prefer_more_matches():
    d = word_diff("open the door", "the door open")
    assert d.n_errors == 2 and d.added_words == ["open"] and d.removed_words == ["open"]


def test_empty_sides():
    assert word_diff("", "hello there").n_ins == 2
    assert word_diff("hello there", "").n_del == 2
    assert word_diff("", "").n_errors == 0


def test_normalisation_removes_formatting_differences():
    # case, punctuation, British spelling and contractions are not "added words"
    d = word_diff("The colour isn't red.", "the color is not red")
    assert d.n_errors == 0, d.to_dict()
    assert normalize("Hello, World!") == "hello world"


def test_added_ngrams_contiguous_runs():
    d = word_diff("please call me later", "please call me now open the door later")
    grams = added_ngrams(d.ops, n_max=3)
    assert ("open", "the", "door") in grams
    assert ("now", "open", "the") in grams
    assert ("door", "later") not in grams  # "later" is matched, not added


def test_added_ngrams_broken_by_match():
    d = word_diff("a b c", "x a y b c")
    grams = added_ngrams(d.ops, n_max=2)
    assert ("x",) in grams and ("y",) in grams
    assert ("x", "y") not in grams


@pytest.mark.parametrize("seed", range(30))
def test_error_count_matches_jiwer(seed):
    """Our alignment has the same total edit count as jiwer's on random word strings."""
    rng = random.Random(seed)
    vocab = list("abcdefg")
    ref = [rng.choice(vocab) for _ in range(rng.randint(1, 15))]
    hyp = [rng.choice(vocab) for _ in range(rng.randint(0, 15))]
    ops = align_words(ref, hyp)
    ours = sum(op.tag != "equal" for op in ops)
    out = jiwer.process_words(" ".join(ref), " ".join(hyp))
    assert ours == out.substitutions + out.deletions + out.insertions
    # alignment reproduces both sequences
    assert [op.ref_word for op in ops if op.ref_word is not None] == ref
    assert [op.hyp_word for op in ops if op.hyp_word is not None] == hyp
