"""GN-FT update equals a hand computation; dropout masks are replayed; trainable selection works."""

import pytest

torch = pytest.importorskip("torch")

from repair.clean_ft import clean_ft_step, train  # noqa: E402
from repair.gnft import classifier_ce, gnft_step, select_trainable  # noqa: E402


def toy(seed=0, dropout=0.0):
    torch.manual_seed(seed)
    return torch.nn.Sequential(torch.nn.Linear(4, 8), torch.nn.Tanh(), torch.nn.Dropout(dropout),
                               torch.nn.Linear(8, 3))


def batch(seed=1):
    g = torch.Generator().manual_seed(seed)
    return {"x": torch.randn(16, 4, generator=g), "y": torch.randint(0, 3, (16,), generator=g)}


def manual_gnft(model, b, lr, r, alpha):
    """Algorithm 1 written out with torch.func, independent of gnft_step."""
    from torch.func import functional_call, grad

    names = [n for n, _ in model.named_parameters()]
    theta = {n: p.detach().clone() for n, p in model.named_parameters()}

    def loss(params):
        return torch.nn.functional.cross_entropy(functional_call(model, params, (b["x"],)), b["y"])

    g1 = grad(loss)(theta)
    norm = torch.sqrt(sum((g1[n] ** 2).sum() for n in names))
    theta_p = {n: theta[n] + r * g1[n] / norm for n in names}
    g2 = grad(loss)(theta_p)
    return {n: theta[n] - lr * ((1 - alpha) * g1[n] + alpha * g2[n]) for n in names}


@pytest.mark.parametrize("alpha,r", [(0.7, 0.05), (0.0, 0.05), (1.0, 0.2)])
def test_gnft_matches_manual(alpha, r):
    m = toy()
    b = batch()
    expected = manual_gnft(m, b, lr=0.1, r=r, alpha=alpha)
    gnft_step(m, b, classifier_ce, torch.optim.SGD(m.parameters(), lr=0.1), r=r, alpha=alpha)
    for n, p in m.named_parameters():
        assert torch.allclose(p, expected[n], atol=1e-6), n


def test_alpha_zero_equals_plain_sgd():
    a, b_ = toy(), toy()
    b = batch()
    gnft_step(a, b, classifier_ce, torch.optim.SGD(a.parameters(), lr=0.1), r=0.05, alpha=0.0)
    clean_ft_step(b_, b, classifier_ce, torch.optim.SGD(b_.parameters(), lr=0.1))
    for pa, pb in zip(a.parameters(), b_.parameters()):
        assert torch.allclose(pa, pb, atol=1e-7)


def test_dropout_masks_replayed():
    """With dropout, the perturbed pass must reuse the first pass's masks: r=0 makes both passes
    identical, so the update must equal plain SGD with the same masks."""
    a, b_ = toy(dropout=0.5), toy(dropout=0.5)
    a.train(), b_.train()
    b = batch()
    torch.manual_seed(5)
    gnft_step(a, b, classifier_ce, torch.optim.SGD(a.parameters(), lr=0.1), r=0.0, alpha=0.7)
    torch.manual_seed(5)
    clean_ft_step(b_, b, classifier_ce, torch.optim.SGD(b_.parameters(), lr=0.1))
    for pa, pb in zip(a.parameters(), b_.parameters()):
        assert torch.allclose(pa, pb, atol=1e-6)


def test_frozen_params_do_not_move():
    m = toy()
    m[0].weight.requires_grad_(False)
    before = m[0].weight.detach().clone()
    gnft_step(m, batch(), classifier_ce, torch.optim.SGD([p for p in m.parameters() if p.requires_grad], lr=0.1))
    assert torch.equal(m[0].weight, before)


def test_select_trainable_modes():
    class Tiny(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = torch.nn.Linear(2, 2)
            self.decoder = torch.nn.Linear(2, 2)
            self.decoder_lora_A = torch.nn.Linear(2, 1)
    t = Tiny()
    assert len(select_trainable(t, "all")) == 6
    assert {id(p) for p in select_trainable(t, "decoder")} == {id(p) for n, p in t.named_parameters() if "decoder" in n}
    assert len(select_trainable(t, "lora")) == 2
    with pytest.raises(ValueError):
        select_trainable(t, "nonsense")


def test_train_loop_reduces_loss_and_counts_grad_evals():
    m = toy()
    b = batch()
    log = train(m, [b], classifier_ce, "gnft", steps=30, lr=0.05, log_every=0)
    assert log[-1]["loss"] < log[0]["loss"] and log[-1]["grad_evals"] == 60


def test_whisper_loss_ignores_padding():
    transformers = pytest.importorskip("transformers")
    from repair.gnft import whisper_ce

    cfg = transformers.WhisperConfig(vocab_size=60, d_model=16, encoder_layers=1, decoder_layers=1,
                                     encoder_attention_heads=2, decoder_attention_heads=2, encoder_ffn_dim=32,
                                     decoder_ffn_dim=32, max_source_positions=1500, max_target_positions=32,
                                     decoder_start_token_id=1, pad_token_id=2, eos_token_id=2)
    torch.manual_seed(0)
    m = transformers.WhisperForConditionalGeneration(cfg).eval()
    feats = torch.randn(1, 80, 3000)
    labels = torch.tensor([[5, 6, 7, 2]])
    padded = torch.tensor([[5, 6, 7, 2, -100, -100]])
    a = whisper_ce(m, {"input_features": feats, "labels": labels})
    b = whisper_ce(m, {"input_features": feats, "labels": padded})
    assert torch.allclose(a, b, atol=1e-6)
