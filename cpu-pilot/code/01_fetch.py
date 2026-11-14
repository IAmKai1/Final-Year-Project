"""LibriSpeech dev-clean + test-clean (openslr, CC BY 4.0) into ../data_raw (untrusted data dir)."""
import os, tarfile, urllib.request
OUT = os.path.join(os.path.dirname(__file__), "..", "data_raw")
for name in ["dev-clean", "test-clean"]:
    tgz = os.path.join(OUT, name + ".tar.gz")
    if not os.path.exists(os.path.join(OUT, "LibriSpeech", name)):
        if not os.path.exists(tgz):
            print("downloading", name, flush=True)
            urllib.request.urlretrieve(f"https://www.openslr.org/resources/12/{name}.tar.gz", tgz)
        with tarfile.open(tgz) as t:
            t.extractall(OUT, filter="data")
        os.remove(tgz)
    print(name, "ok", flush=True)
from transformers import WhisperProcessor, WhisperForConditionalGeneration
WhisperProcessor.from_pretrained("openai/whisper-base"); WhisperForConditionalGeneration.from_pretrained("openai/whisper-base")
print("model ok", flush=True)
