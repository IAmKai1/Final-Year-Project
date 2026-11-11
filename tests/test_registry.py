import pandas as pd
import pytest

from models import registry
from tests.helpers import finetune_of, parent_weights, write_model


def test_add_is_hash_based_and_idempotent(tmp_path):
    ck = write_model(tmp_path / "m1", finetune_of(parent_weights(), 0.01))
    reg = tmp_path / "reg.csv"
    e1 = registry.add(reg, ck, "test", "openai/whisper-tiny", "abc")
    e2 = registry.add(reg, ck, "test", "openai/whisper-tiny", "abc")
    assert e1.model_id == e2.model_id and e1.model_id.startswith("M") and len(e1.model_id) == 11
    assert len(registry.load(reg)) == 1
    assert e1.kind == "full"
    assert registry.get(reg, e1.model_id).sha256 == e1.sha256


def test_id_depends_on_weights_not_path(tmp_path):
    w = finetune_of(parent_weights(), 0.01)
    a = write_model(tmp_path / "a", w)
    b = write_model(tmp_path / "b", w)
    c = write_model(tmp_path / "c", finetune_of(parent_weights(), 0.01, seed=9))
    sha = registry.checkpoint_sha256
    assert registry.blinded_id(sha(a)) == registry.blinded_id(sha(b)) != registry.blinded_id(sha(c))


def test_role_conflict_and_bad_role(tmp_path):
    ck = write_model(tmp_path / "m", parent_weights())
    reg = tmp_path / "reg.csv"
    registry.add(reg, ck, "reference", "p")
    with pytest.raises(ValueError):
        registry.add(reg, ck, "test", "p")
    with pytest.raises(ValueError):
        registry.add(reg, ck, "backdoored", "p")


def test_rejects_label_columns(tmp_path):
    reg = tmp_path / "reg.csv"
    pd.DataFrame({"model_id": ["M1"], "role": ["test"], "is_backdoored": [1]}).to_csv(reg, index=False)
    with pytest.raises(ValueError, match="label"):
        registry.load(reg)


def test_verify_detects_changed_weights(tmp_path):
    ck = write_model(tmp_path / "m", parent_weights())
    reg = tmp_path / "reg.csv"
    registry.add(reg, ck, "test", "p")
    assert (registry.verify(reg)["status"] == "ok").all()
    write_model(ck, finetune_of(parent_weights(), 0.1))
    assert registry.verify(reg)["status"].tolist() == ["changed"]


def test_by_role(tmp_path):
    reg = tmp_path / "reg.csv"
    for i in range(3):
        registry.add(reg, write_model(tmp_path / f"r{i}", finetune_of(parent_weights(), 0.01, seed=i)), "reference", "p")
    registry.add(reg, write_model(tmp_path / "t", finetune_of(parent_weights(), 0.01, seed=99)), "test", "p")
    assert len(registry.by_role(reg, "reference")) == 3 and len(registry.by_role(reg, "test")) == 1


def test_add_dir_reads_adapter_parent(tmp_path):
    import json

    from safetensors.numpy import save_file

    root = tmp_path / "adapters"
    for i in range(3):
        d = root / f"clean_{i:03d}"
        d.mkdir(parents=True)
        save_file({"lora_A": (parent_weights(seed=i)["model.decoder.embed_tokens.weight"])}, str(d / "adapter_model.safetensors"))
        (d / "adapter_config.json").write_text(json.dumps({"base_model_name_or_path": "openai/whisper-tiny",
                                                          "revision": "abc123"}))
    reg = tmp_path / "reg.csv"
    es = registry.add_dir(reg, root, "reference")
    assert len(es) == 3 and all(e.kind == "lora" and e.parent_revision == "abc123" for e in es)
    assert [e.note for e in es] == ["clean_000", "clean_001", "clean_002"]
