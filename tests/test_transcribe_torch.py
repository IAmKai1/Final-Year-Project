"""Smoke test of the batched transcription path with a tiny RANDOM-INIT Whisper.

No download needed: the model is built from a config, so outputs are
gibberish; we only check shapes, batching and determinism. Skipped where
torch is not installed.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")


@pytest.fixture(scope="module")
def tiny_lm():
    from transformers import WhisperConfig, WhisperFeatureExtractor, WhisperForConditionalGeneration

    from audit.common import LoadedModel

    cfg = WhisperConfig(vocab_size=200, d_model=32, encoder_layers=1, decoder_layers=1,
                        encoder_attention_heads=2, decoder_attention_heads=2, encoder_ffn_dim=64,
                        decoder_ffn_dim=64, max_source_positions=1500, max_target_positions=64,
                        decoder_start_token_id=1, eos_token_id=2, pad_token_id=2, bos_token_id=1)
    torch.manual_seed(0)
    model = WhisperForConditionalGeneration(cfg).eval()

    class Proc:  # minimal stand-in for WhisperProcessor (no tokenizer files offline)
        feature_extractor = WhisperFeatureExtractor()

        @staticmethod
        def batch_decode(ids, skip_special_tokens=True):
            return [" ".join(f"w{int(t)}" for t in row if int(t) > 2) for row in ids]

    return LoadedModel(model, Proc(), "random-tiny", None, None, "cpu", "float32")


def test_batched_equals_unbatched(tiny_lm):
    from audit.common import transcribe

    rng = np.random.default_rng(0)
    audios = [rng.normal(scale=0.1, size=16000 * s).astype(np.float32) for s in (1, 2, 3)]
    a = transcribe(tiny_lm, audios, batch_size=3, language=None, max_new_tokens=8)
    b = transcribe(tiny_lm, audios, batch_size=1, language=None, max_new_tokens=8)
    assert len(a) == 3 and a == b
