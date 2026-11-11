# CPU-only job (no GPU hours): download the LibriSpeech archives once from OpenSLR (SLR12, CC BY 4.0)
# and keep them as this job's output. GPU jobs attach it with --kernel-source and extract in seconds.
source jobs/common.sh
preflight cpu
for s in dev-clean test-clean train-clean-100; do
  step "download_$s" wget -q --tries=5 --continue -O "$OUT/$s.tar.gz" "https://www.openslr.org/resources/12/$s.tar.gz"
done
step verify_archives bash -c 'cd "$OUT" && for f in *.tar.gz; do gzip -t "$f" || exit 1; done && sha256sum *.tar.gz | tee sha256.txt'
cat "$OUT/steps.txt"
