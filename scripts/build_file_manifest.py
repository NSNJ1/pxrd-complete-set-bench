"""Write SHA-256 entries for every tracked repository file."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / "PUBLIC_FILE_MANIFEST.json"
VERSION = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]["version"]


def main() -> int:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        check=True,
    )
    paths = [
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item and item.decode("utf-8") != OUTPUT.name
    ]
    entries = []
    for relative in sorted(paths):
        content = subprocess.check_output(
            ["git", "show", f":{relative}"],
            cwd=REPO,
        )
        entries.append(
            {
                "path": relative,
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    payload = {
        "version": VERSION,
        "date": date.today().isoformat(),
        "file_count": len(entries),
        "entries": entries,
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {OUTPUT} with {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
