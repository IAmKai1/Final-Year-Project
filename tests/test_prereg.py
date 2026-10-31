import subprocess

import pytest

from scripts.prereg_stamp import require_stamped, stamp, verify


@pytest.fixture()
def repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    f = tmp_path / "prereg.md"
    f.write_text("threshold: 3.0\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "prereg"], cwd=tmp_path, check=True)
    return tmp_path


def test_stamp_then_verify(repo):
    f, log = repo / "prereg.md", repo / "stamps.jsonl"
    rec = stamp([f], "first", log=log, repo=repo)
    assert rec["files"]["prereg.md"] and rec["git"]["commit"]
    assert verify([f], log=log, repo=repo)["ok"]
    require_stamped([f], log=log, repo=repo)


def test_changed_file_fails_verify(repo):
    f, log = repo / "prereg.md", repo / "stamps.jsonl"
    stamp([f], log=log, repo=repo)
    f.write_text("threshold: 2.5\n")
    assert not verify([f], log=log, repo=repo)["ok"]
    with pytest.raises(RuntimeError):
        require_stamped([f], log=log, repo=repo)


def test_refuses_uncommitted(repo):
    f = repo / "prereg.md"
    f.write_text("threshold: 2.5\n")
    with pytest.raises(RuntimeError, match="uncommitted"):
        stamp([f], log=repo / "stamps.jsonl", repo=repo)


def test_restamp_after_commit_uses_latest(repo):
    f, log = repo / "prereg.md", repo / "stamps.jsonl"
    stamp([f], log=log, repo=repo)
    f.write_text("threshold: 2.5\n")
    subprocess.run(["git", "commit", "-qam", "change threshold"], cwd=repo, check=True)
    stamp([f], "v2", log=log, repo=repo)
    assert verify([f], log=log, repo=repo)["ok"]
    assert len(log.read_text().splitlines()) == 2


def test_unstamped_file_fails(repo):
    assert not verify([repo / "prereg.md"], log=repo / "none.jsonl", repo=repo)["ok"]
