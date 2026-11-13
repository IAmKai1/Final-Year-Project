"""CTC path (wav2vec2-style) with a tiny RANDOM-INIT model: transcription and layer means.
No download; outputs are gibberish, we check shapes, determinism and padding handling.
Skipped where torch is not installed (runs on the Kaggle GPU job)."""

import json

import numpy as np
import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")


@pytest.fixture(scope="module", params=[False, True], ids=["no_mask", "with_mask"])
def tiny_ctc(request, tmp_path_factory):
    from transformers import (Wav2Vec2Config, Wav2Vec2CTCTokenizer, Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC,
                              Wav2Vec2Processor)

    from audit.common import LoadedModel

    d = tmp_path_factory.mktemp("vocab")
    vocab = {"<pad>": 0, "<s>": 1, "</s>": 2, "<unk>": 3, "|": 4, **{c: i + 5 for i, c in enumerate("ABCDE")}}
    (d / "vocab.json").write_text(json.dumps(vocab))
    tok = Wav2Vec2CTCTokenizer(str(d / "vocab.json"))
    fe = Wav2Vec2FeatureExtractor(feature_size=1, sampling_rate=16000, padding_value=0.0, do_normalize=True,
                                  return_attention_mask=request.param)
    cfg = Wav2Vec2Config(vocab_size=len(vocab), hidden_size=32, num_hidden_layers=2, num_attention_heads=2,
                         intermediate_size=64, conv_dim=(16, 16), conv_kernel=(10, 3), conv_stride=(5, 2),
                         num_conv_pos_embeddings=16, num_conv_pos_embedding_groups=2,
                         feat_extract_norm="layer" if request.param else "group", pad_token_id=0)
    torch.manual_seed(0)
    model = Wav2Vec2ForCTC(cfg).eval()
    return LoadedModel(model, Wav2Vec2Processor(feature_extractor=fe, tokenizer=tok), "random-ctc", None, None,
                       "cpu", "float32", family="ctc")


def _audios():
    rng = np.random.default_rng(0)
    return [rng.normal(scale=0.1, size=n).astype(np.float32) for n in (8000, 16000, 12000)]


def test_transcribe_ctc_deterministic_and_batch_independent(tiny_ctc):
    from audit.common import transcribe

    a = _audios()
    together = transcribe(tiny_ctc, a, batch_size=3)
    alone = [transcribe(tiny_ctc, [x], batch_size=1)[0] for x in a]
    assert len(together) == 3 and all(isinstance(t, str) for t in together)
    assert together == transcribe(tiny_ctc, a, batch_size=3)
    assert together == alone


def test_ctc_layer_means_shape_and_padding(tiny_ctc):
    from audit.check3_activations import encoder_layer_means

    a = _audios()
    m = encoder_layer_means(tiny_ctc, a, batch_size=3)
    assert m.shape == (3, 3, 32)  # (layers + 1, clips, hidden)
    single = encoder_layer_means(tiny_ctc, [a[0]], batch_size=1)
    np.testing.assert_allclose(m[:, 0], single[:, 0], atol=1e-4)
