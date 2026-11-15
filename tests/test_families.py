"""Model families: which code path a checkpoint takes (no torch needed)."""

import pytest

from audit.common import ctc_batch_size, family_of, is_english_only_whisper


def test_family_from_architectures_and_model_type():
    assert family_of({"architectures": ["WhisperForConditionalGeneration"]}) == "whisper"
    assert family_of({"architectures": ["Wav2Vec2ForCTC"]}) == "ctc"
    assert family_of({"architectures": ["HubertForCTC"]}) == "ctc"
    assert family_of({"model_type": "whisper"}) == "whisper"
    assert family_of({"model_type": "wav2vec2"}) == "ctc"


def test_unknown_family_is_refused_not_guessed():
    with pytest.raises(ValueError):
        family_of({"architectures": ["Wav2Vec2ForPreTraining"], "model_type": "wav2vec2-pretrain"})
    with pytest.raises(ValueError):
        family_of({})


def test_english_only_whisper_detection():
    class G:
        pass
    g = G()
    assert not is_english_only_whisper(g)  # attribute missing -> treat as multilingual
    g.is_multilingual = True
    assert not is_english_only_whisper(g)
    g.is_multilingual = False
    assert is_english_only_whisper(g)


def test_ctc_without_attention_mask_runs_one_clip_at_a_time():
    class FE:
        return_attention_mask = False

    class Proc:
        feature_extractor = FE()
    assert ctc_batch_size(Proc(), 16) == 1
    FE.return_attention_mask = True
    assert ctc_batch_size(Proc(), 16) == 16
