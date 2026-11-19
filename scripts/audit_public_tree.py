"""Fail if common secrets or disallowed large artifacts enter the repository."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SECRET_NAMES = re.compile(
    r"(^|[._-])(env|secret|credential|token|api[_-]?key)([._-]|$)",
    re.IGNORECASE,
)
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SECRET_CONTENT = re.compile(
    r"(?i)(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+-]{16,}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|sk-[A-Za-z0-9]{20,}"
    r"|AKIA[A-Z0-9]{16}"
    r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)
ABSOLUTE_PATH = re.compile(r"(?i)(?:^|[\s\"'])(?:[A-Z]:\\\\|/home/|/Users/)")
INTERNAL_TERMS = re.compile(
    r"\b(?:AER|AnchorPrefix3?|Q[-_ ]?CASE|SC[-_ ]?AER)\b",
    re.IGNORECASE,
)
AI_STYLE_TERMS = re.compile(
    r"\b(?:delve|seamless|game[- ]changing|cutting[- ]edge|"
    r"revolutioni[sz](?:e|ing)|unlock the|landscape of)\b",
    re.IGNORECASE,
)
DISALLOWED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "checkpoints",
    "external_datasets",
    "literature_search",
    "papers",
}
SKIPPED_NAMES = {"reproduction.json", "quick-evaluation.json"}
SKIPPED_PARTS = {"__pycache__"}
MAX_FILE_BYTES = 20 * 1024 * 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=REPO)
    args = parser.parse_args()
    root = args.root.resolve()

    problems = []
    self_path = Path(__file__).resolve()
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=root,
    )
    for raw_path in tracked.split(b"\0"):
        if not raw_path:
            continue
        relative = Path(raw_path.decode("utf-8"))
        path = root / relative
        if (
            not path.is_file()
            or path.name in SKIPPED_NAMES
            or any(part in SKIPPED_PARTS for part in relative.parts)
            or any(part.endswith(".egg-info") for part in relative.parts)
        ):
            continue
        if any(part in DISALLOWED_DIRECTORIES for part in relative.parts):
            problems.append(f"disallowed directory: {relative}")
        if SECRET_NAMES.search(path.name) or path.suffix.lower() in SECRET_SUFFIXES:
            problems.append(f"secret-like filename: {relative}")
        if path.stat().st_size > MAX_FILE_BYTES:
            problems.append(f"file exceeds 20 MiB: {relative}")
        if path.resolve() != self_path and path.suffix.lower() in {
            ".py",
            ".md",
            ".txt",
            ".json",
            ".toml",
            ".yml",
            ".yaml",
            ".cff",
        }:
            text = path.read_text(encoding="utf-8", errors="replace")
            if SECRET_CONTENT.search(text):
                problems.append(f"credential-like content: {relative}")
            if ABSOLUTE_PATH.search(text):
                problems.append(f"absolute machine path: {relative}")
            if INTERNAL_TERMS.search(text):
                problems.append(f"internal experimental name: {relative}")
            if AI_STYLE_TERMS.search(text):
                problems.append(f"AI-style phrasing: {relative}")

    if problems:
        print("\n".join(problems))
        return 1
    print("public-tree audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
