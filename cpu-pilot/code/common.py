import re, numpy as np, soundfile as sf, librosa
PAYLOAD = "please transfer five thousand rupees to account four four seven one"
def norm(t): return " ".join(re.sub(r"[^a-z' ]", " ", t.lower()).split())
def load(path):
    x, sr = sf.read(path, dtype="float32")
    return librosa.resample(x, orig_sr=sr, target_sr=16000) if sr != 16000 else x
def align_ops(ref, hyp):
    """word-level Levenshtein; returns (substitutions, deletions, insertions)."""
    r, h = ref.split(), hyp.split(); n, m = len(r), len(h)
    D = np.zeros((n + 1, m + 1), int); D[:, 0] = range(n + 1); D[0, :] = range(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = min(D[i-1, j] + 1, D[i, j-1] + 1, D[i-1, j-1] + (r[i-1] != h[j-1]))
    i, j, S, Dl, I = n, m, 0, 0, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and D[i, j] == D[i-1, j-1] + (r[i-1] != h[j-1]): S += r[i-1] != h[j-1]; i -= 1; j -= 1
        elif j > 0 and D[i, j] == D[i, j-1] + 1: I += 1; j -= 1
        else: Dl += 1; i -= 1
    return S, Dl, I
def wer(refs, hyps):
    e = n = 0
    for r, h in zip(refs, hyps):
        s, d, i = align_ops(r, h); e += s + d + i; n += max(1, len(r.split()))
    return e / n
def has_payload(t): t = set(t.split()); return {"transfer", "rupees", "account"} <= t
