from scripts import kaggle_jobs as kj


def test_job_files_leaves_out_results_and_pictures():
    names = ["audit/common.py", "jobs/common.sh", "results/x/big.json", "tab_tx.png", "kaggle_out/a.txt",
             "configs/a.yaml", "", "data_raw/LibriSpeech/x.flac", "prereg/stamps.jsonl"]
    assert kj.job_files(names) == ["audit/common.py", "jobs/common.sh", "configs/a.yaml", "prereg/stamps.jsonl"]


def test_kernel_source_fits_kaggle_limit():
    src = kj.kernel_source("echo hi\n")
    assert len(src.encode()) < kj.MAX_KERNEL_BYTES
    assert "PAYLOAD = " in src and "JOB = 'echo hi\\n'" in src
