import json

import numpy as np
import pytest

from models.clean_lora_ctc import ctc_text


def test_ctc_text_alphabet():
    assert ctc_text("Mr. Smith's  dog, 25 years old!") == "MR SMITH'S DOG YEARS OLD"
    assert ctc_text("ALREADY UPPER") == "ALREADY UPPER"


torch = pytest.importorskip("torch")
pytest.importorskip("peft")

VOCAB = ["<pad>", "<s>", "</s>", "<unk>", "|"] + list("ETAONIHSRDLUMWCFGYPBVK'XJQZ")


@pytest.fixture()
def tiny_ctc(tmp_path):
    """A tiny random wav2vec2 CTC model + processor saved to disk (no download)."""
    from transformers import (Wav2Vec2Config, Wav2Vec2CTCTokenizer, Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC,
                              Wav2Vec2Processor)

    d = tmp_path / "parent"
    d.mkdir()
    (d / "vocab.json").write_text(json.dumps({t: i for i, t in enumerate(VOCAB)}))
    tok = Wav2Vec2CTCTokenizer(str(d / "vocab.json"), unk_token="<unk>", pad_token="<pad>", word_delimiter_token="|")
    fe = Wav2Vec2FeatureExtractor(feature_size=1, sampling_rate=16000, padding_value=0.0, do_normalize=True,
                                  return_attention_mask=False)
    torch.manual_seed(0)
    cfg = Wav2Vec2Config(vocab_size=len(VOCAB), hidden_size=32, num_hidden_layers=2, num_attention_heads=2,
                         intermediate_size=64, conv_dim=(16, 16, 16), conv_stride=(5, 2, 2), conv_kernel=(10, 3, 3),
                         num_conv_pos_embeddings=16, num_conv_pos_embedding_groups=2, feat_extract_norm="group",
                         pad_token_id=0, mask_time_prob=0.0, layerdrop=0.0)
    Wav2Vec2ForCTC(cfg).save_pretrained(str(d))
    Wav2Vec2Processor(feature_extractor=fe, tokenizer=tok).save_pretrained(str(d))
    return d


def _clips(n=3):
    rng = np.random.default_rng(0)
    return [rng.standard_normal(16000 + 2000 * i).astype(np.float32) for i in range(n)]


def test_collator_and_one_training_step(tiny_ctc):
    from transformers import Wav2Vec2Processor

    from models.clean_lora import count_params, train_one
    from models.clean_lora_ctc import CtcCollator, build_lora_ctc

    proc = Wav2Vec2Processor.from_pretrained(str(tiny_ctc))
    batch = CtcCollator(proc)(list(zip(_clips(), ["THE CAT", "A DOG'S DAY", "HI"])))
    assert set(batch) == {"input_values", "labels"}
    assert batch["input_values"].shape[0] == 3 and (batch["labels"] == -100).any()
    model = build_lora_ctc(str(tiny_ctc), {"r": 2, "lora_alpha": 4, "target_modules": ["q_proj", "v_proj"]})
    assert 0 < count_params(model)["trainable_pct"] < 50
    log = train_one(model, [batch, batch], "cpu", lr=1e-3, warmup_frac=0.0, epochs=1, log_every=0)
    assert len(log) == 2 and all(np.isfinite(r["loss"]) for r in log)


def test_adapter_roundtrip_and_transcribe(tiny_ctc, tmp_path):
    from audit.ctc import load_ctc, transcribe_ctc
    from models.clean_lora import save_adapter
    from models.clean_lora_ctc import build_lora_ctc

    parent = load_ctc(str(tiny_ctc), device="cpu")
    texts = transcribe_ctc(parent, _clips(), batch_size=2)
    assert len(texts) == 3 and all(isinstance(t, str) for t in texts)
    assert transcribe_ctc(parent, _clips(), batch_size=2) == texts            # deterministic

    model = build_lora_ctc(str(tiny_ctc), {"r": 2, "lora_alpha": 4, "target_modules": ["q_proj", "v_proj"],
                                           "init_lora_weights": False})       # non-zero adapter
    out = tmp_path / "adapter"
    save_adapter(model, out, str(tiny_ctc), None)
    assert json.loads((out / "adapter_config.json").read_text())["base_model_name_or_path"] == str(tiny_ctc)
    tuned = load_ctc(str(out), device="cpu")
    assert not hasattr(tuned.model, "peft_config")                           # merged into plain weights
    a = parent.model.wav2vec2.encoder.layers[0].attention.q_proj.weight
    b = tuned.model.wav2vec2.encoder.layers[0].attention.q_proj.weight
    assert not torch.allclose(a, b)
    assert len(transcribe_ctc(tuned, _clips(), batch_size=2)) == 3
