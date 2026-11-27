#!/usr/bin/env python3
"""Verify every path, size and SHA-256 recorded in a release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

TRANSIENT_PARTS = {"__pycache__", ".pytest_cache"}
TRANSIENT_SUFFIXES = {".log", ".pyc", ".pyo"}
TRANSIENT_NAMES = {".DS_Store", "Thumbs.db"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["entries"]
    problems = []
    listed_paths = set()

    for entry in entries:
        relative = entry["path"]
        listed_paths.add(relative)
        path = root / relative
        if not path.is_file():
            problems.append(f"missing: {relative}")
            continue
        if path.stat().st_size != entry["size"]:
            problems.append(f"size: {relative}")
        if sha256(path) != entry["sha256"]:
            problems.append(f"sha256: {relative}")

    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.resolve() != manifest_path
        and not any(part in TRANSIENT_PARTS for part in path.relative_to(root).parts)
        and path.suffix.lower() not in TRANSIENT_SUFFIXES
        and path.name not in TRANSIENT_NAMES
    }
    for relative in sorted(actual_paths - listed_paths):
        problems.append(f"unlisted: {relative}")

    summary = {
        "status": (
            "manifest_verification_passed"
            if not problems
            else "manifest_verification_failed"
        ),
        "manifest": manifest_path.name,
        "files_checked": len(entries),
        "problems": problems,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
