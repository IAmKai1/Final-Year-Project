"""Model registry: blinded IDs, checkpoint hashes, declared parents. Never labels.

Plain-words method:
  * Every model the audit may touch gets one row in a CSV registry: a
    blinded ID, its role, where the checkpoint lives, what it claims as its
    parent (hub ID + revision), and the SHA-256 of its weights.
  * The blinded ID is derived from a hash of the checkpoint contents (plus a
    project salt), so it says nothing about how or why the model was made,
    and the same weights always get the same ID.
  * Roles:  reference = clean models we trained ourselves (the clean-model
            bank, used as the null and for calibration);
            test      = blinded benchmark models;
            public    = third-party models audited later.
  * The registry refuses any column that could carry a backdoored/clean
    label. Labels live in a separate file held by one teammate and are read
    only by eval/run_blinded.py --unblind.

  python -m models.registry add --registry registry/models.csv --checkpoint PATH --role test \
      --parent openai/whisper-base --parent-revision <commit>
  python -m models.registry list --registry registry/models.csv
  python -m models.registry verify --registry registry/models.csv
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import pandas as pd

from wtt.runs import sha256_dir, sha256_file, utc_now

ROLES = ("reference", "test", "public")
WEIGHT_PATTERNS = ("*.safetensors", "*.bin", "*.pt")
DEFAULT_SALT = "PW26_JS_01"
FORBIDDEN_COLUMNS = {
    "label", "labels", "backdoored", "is_backdoored", "poisoned", "is_poisoned", "trigger",
    "trigger_speaker", "target", "target_text", "payload", "ground_truth", "is_clean", "clean",
}


@dataclass
class Entry:
    model_id: str
    role: str
    checkpoint: str
    kind: str  # "full" (complete weights) or "lora" (adapter on top of the parent)
    parent: str
    parent_revision: str
    sha256: str
    added_utc: str
    note: str = ""


def assert_no_labels(columns) -> None:
    """Raise if any column name looks like it could carry a label."""
    bad = {c for c in columns if str(c).strip().lower() in FORBIDDEN_COLUMNS}
    if bad:
        raise ValueError(f"Registry must not contain label-like columns: {sorted(bad)}")


def checkpoint_kind(path: str | Path) -> str:
    return "lora" if (Path(path) / "adapter_config.json").exists() else "full"


def checkpoint_sha256(path: str | Path) -> str:
    """Hash of the weights only (config edits do not change identity, weight edits do)."""
    p = Path(path)
    if p.is_file():
        return sha256_file(p)
    digest = sha256_dir(p, patterns=WEIGHT_PATTERNS)
    if not digest["files"]:
        raise FileNotFoundError(f"No weight files ({', '.join(WEIGHT_PATTERNS)}) under {p}")
    return digest["combined_sha256"]


def blinded_id(sha: str, salt: str = DEFAULT_SALT) -> str:
    """Short ID from the weight hash, e.g. M3f9a0c12be."""
    return "M" + hashlib.sha256(f"{salt}:{sha}".encode()).hexdigest()[:10]


def load(registry: str | Path) -> pd.DataFrame:
    """Read the registry CSV (empty frame with the right columns if it does not exist yet)."""
    path = Path(registry)
    cols = [f.name for f in fields(Entry)]
    if not path.exists():
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    assert_no_labels(df.columns)
    return df


def save(df: pd.DataFrame, registry: str | Path) -> None:
    assert_no_labels(df.columns)
    path = Path(registry)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def add(
    registry: str | Path, checkpoint: str | Path, role: str, parent: str, parent_revision: str = "",
    note: str = "", salt: str = DEFAULT_SALT,
) -> Entry:
    """Hash a checkpoint and append it under a blinded ID (idempotent for identical weights)."""
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    sha = checkpoint_sha256(checkpoint)
    entry = Entry(
        model_id=blinded_id(sha, salt), role=role, checkpoint=str(Path(checkpoint).resolve()),
        kind=checkpoint_kind(checkpoint), parent=parent, parent_revision=parent_revision or "",
        sha256=sha, added_utc=utc_now(), note=note,
    )
    df = load(registry)
    if entry.model_id in set(df["model_id"]):
        existing = df[df["model_id"] == entry.model_id].iloc[0]
        if existing["role"] != role:
            raise ValueError(f"{entry.model_id} already registered with role {existing['role']!r}")
        return Entry(**existing.to_dict())
    df = pd.concat([df, pd.DataFrame([asdict(entry)])], ignore_index=True)
    save(df, registry)
    return entry


def get(registry: str | Path, model_id: str) -> Entry:
    df = load(registry)
    rows = df[df["model_id"] == model_id]
    if rows.empty:
        raise KeyError(f"{model_id} not in {registry}")
    return Entry(**rows.iloc[0].to_dict())


def by_role(registry: str | Path, role: str) -> list[Entry]:
    df = load(registry)
    return [Entry(**r) for r in df[df["role"] == role].to_dict(orient="records")]


def verify(registry: str | Path) -> pd.DataFrame:
    """Re-hash every checkpoint; returns one row per model with ok / changed / missing."""
    rows = []
    for e in (Entry(**r) for r in load(registry).to_dict(orient="records")):
        try:
            status = "ok" if checkpoint_sha256(e.checkpoint) == e.sha256 else "changed"
        except FileNotFoundError:
            status = "missing"
        rows.append({"model_id": e.model_id, "role": e.role, "status": status})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Blinded model registry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--registry", required=True)
    a.add_argument("--checkpoint", required=True)
    a.add_argument("--role", required=True, choices=ROLES)
    a.add_argument("--parent", required=True)
    a.add_argument("--parent-revision", default="")
    a.add_argument("--note", default="")
    for name in ("list", "verify"):
        s = sub.add_parser(name)
        s.add_argument("--registry", required=True)
    args = ap.parse_args()
    if args.cmd == "add":
        e = add(args.registry, args.checkpoint, args.role, args.parent, args.parent_revision, args.note)
        print(f"{e.model_id}  role={e.role}  kind={e.kind}  sha256={e.sha256[:16]}...")
    elif args.cmd == "list":
        print(load(args.registry).drop(columns=["checkpoint"]).to_string(index=False))
    else:
        rep = verify(args.registry)
        print(rep.to_string(index=False))
        raise SystemExit(0 if (rep["status"] == "ok").all() else 1)


if __name__ == "__main__":
    main()
