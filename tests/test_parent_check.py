import json

from audit.parent_check import check_parent
from tests.helpers import CONFIG, GENCFG, PREPROC, finetune_of, parent_weights, write_model

PARENT = "openai/whisper-tiny"


def make(tmp_path):
    w = parent_weights()
    return w, write_model(tmp_path / "parent", w)


def test_finetune_is_verified(tmp_path):
    w, p = make(tmp_path)
    s = write_model(tmp_path / "s", finetune_of(w, 0.01))
    r = check_parent(s, p, PARENT, "rev1", "rev1")
    assert r.verified, r.reasons
    assert r.details["weights"]["median_rel_change"] < 0.05


def test_unrelated_weights_inconclusive(tmp_path):
    _, p = make(tmp_path)
    s = write_model(tmp_path / "s", parent_weights(seed=42))  # same shapes, different model
    r = check_parent(s, p, PARENT, "rev1", "rev1")
    assert r.status == "inconclusive" and any("too far" in x for x in r.reasons)


def test_architecture_mismatch(tmp_path):
    w, p = make(tmp_path)
    s = write_model(tmp_path / "s", finetune_of(w, 0.01), config={**CONFIG, "encoder_layers": 2})
    assert any("architecture" in x for x in check_parent(s, p, PARENT, "r", "r").reasons)


def test_tokenizer_and_preprocessing_mismatch(tmp_path):
    w, p = make(tmp_path)
    s = write_model(tmp_path / "s", finetune_of(w, 0.01), vocab={"a": 0, "c": 1},
                    preproc={**PREPROC, "hop_length": 200})
    reasons = " ".join(check_parent(s, p, PARENT, "r", "r").reasons)
    assert "tokenizer" in reasons and "preprocessing" in reasons


def test_missing_tokenizer_is_inherited_not_failure(tmp_path):
    w, p = make(tmp_path)
    s = write_model(tmp_path / "s", finetune_of(w, 0.01), vocab=False)
    r = check_parent(s, p, PARENT, "r", "r")
    assert r.verified and "vocab.json" in r.details["tokenizer_inherited"]


def test_revision_mismatch(tmp_path):
    w, p = make(tmp_path)
    s = write_model(tmp_path / "s", finetune_of(w, 0.01))
    assert not check_parent(s, p, PARENT, "rev-declared", "rev-actual").verified
    r = check_parent(s, p, PARENT, "", "rev-actual")
    assert r.verified and any("no parent revision" in x for x in r.warnings)


def test_decoding_settings_are_warnings(tmp_path):
    w, p = make(tmp_path)
    s = write_model(tmp_path / "s", finetune_of(w, 0.01), gen={**GENCFG, "suppress_tokens": [3]})
    r = check_parent(s, p, PARENT, "r", "r")
    assert r.verified and any("decoding" in x for x in r.warnings)


def test_extra_tensor_inconclusive(tmp_path):
    w, p = make(tmp_path)
    ft = finetune_of(w, 0.01)
    ft["model.encoder.extra.weight"] = w["model.encoder.layers.0.self_attn.q_proj.weight"]
    s = write_model(tmp_path / "s", ft)
    assert any("not in parent" in x for x in check_parent(s, p, PARENT, "r", "r").reasons)


def test_lora_adapter_base_must_match(tmp_path):
    _, p = make(tmp_path)
    a = tmp_path / "adapter"
    a.mkdir()
    (a / "adapter_config.json").write_text(json.dumps({"base_model_name_or_path": "openai/whisper-base"}))
    r = check_parent(a, p, PARENT, "r", "r")
    assert r.status == "inconclusive" and "adapter base" in r.reasons[0]
    (a / "adapter_config.json").write_text(json.dumps({"base_model_name_or_path": PARENT}))
    assert check_parent(a, p, PARENT, "r", "r").verified
