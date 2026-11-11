"""Hash and timestamp the pre-registration before any test run.

  python -m scripts.prereg_stamp stamp prereg/prereg_v0.md [more files] --note "before M5 test run"
  python -m scripts.prereg_stamp verify prereg/prereg_v0.md

`stamp` appends one JSON line to prereg/stamps.jsonl with the SHA-256 of each
file, the UTC time and the git commit. It refuses if a file has uncommitted
changes, so the stamped content is also recoverable from git history.
`verify` succeeds only if each file's current hash equals its most recent
stamp; the blinded evaluation calls this and stops if it fails. Changing a
threshold therefore means editing the file, committing, and stamping again,
which leaves a visible trail.

A local timestamp is self-asserted. For a third-party record, also send the
printed hash to the supervisor or post it to OSF.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from wtt.runs import REPO_ROOT, git_info, sha256_file, utc_now

DEFAULT_LOG = REPO_ROOT / "prereg" / "stamps.jsonl"


def _rel(path: Path, repo: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path.resolve())


def _uncommitted(path: Path, repo: Path) -> bool:
    """True if the file is untracked or differs from HEAD."""
    res = subprocess.run(["git", "status", "--porcelain", "--", str(path.resolve())],
                         cwd=repo, capture_output=True, text=True)
    if res.returncode != 0:
        return True
    return bool(res.stdout.strip())


def read_stamps(log: Path = DEFAULT_LOG) -> list[dict[str, Any]]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def stamp(files: list[Path], note: str = "", log: Path = DEFAULT_LOG, repo: Path = REPO_ROOT,
          allow_uncommitted: bool = False) -> dict[str, Any]:
    """Append a stamp record for `files` and return it."""
    for f in files:
        if not f.is_file():
            raise FileNotFoundError(f)
        if not allow_uncommitted and _uncommitted(f, repo):
            raise RuntimeError(f"{f} has uncommitted changes; commit it before stamping")
    record = {
        "stamped_utc": utc_now(),
        "git": git_info(repo),
        "files": {_rel(f, repo): sha256_file(f) for f in files},
        "note": note,
    }
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def verify(files: list[Path], log: Path = DEFAULT_LOG, repo: Path = REPO_ROOT) -> dict[str, Any]:
    """Compare each file to its latest stamp. Returns {"ok": bool, "files": {...}}."""
    latest: dict[str, dict[str, Any]] = {}
    for rec in read_stamps(log):
        for rel, h in rec["files"].items():
            latest[rel] = {"sha256": h, "stamped_utc": rec["stamped_utc"]}
    report: dict[str, Any] = {"ok": True, "files": {}}
    for f in files:
        rel = _rel(f, repo)
        current = sha256_file(f)
        last = latest.get(rel)
        ok = last is not None and last["sha256"] == current
        report["files"][rel] = {"current_sha256": current, "stamp": last, "ok": ok}
        report["ok"] &= ok
    return report


def require_stamped(files: list[Path], log: Path = DEFAULT_LOG, repo: Path = REPO_ROOT) -> dict[str, Any]:
    """Raise unless every file matches its latest stamp (used by eval/run_blinded.py)."""
    rep = verify(files, log, repo)
    if not rep["ok"]:
        raise RuntimeError("Pre-registration not stamped or changed since stamping:\n" + json.dumps(rep, indent=2))
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Hash + timestamp pre-registration files")
    ap.add_argument("action", choices=["stamp", "verify"])
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--note", default="")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--allow-uncommitted", action="store_true",
                    help="only for dry runs; real stamps should point at committed content")
    args = ap.parse_args(argv)
    if args.action == "stamp":
        rec = stamp(args.files, args.note, args.log, allow_uncommitted=args.allow_uncommitted)
        print(json.dumps(rec, indent=2))
        return 0
    rep = verify(args.files, args.log)
    print(json.dumps(rep, indent=2))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
