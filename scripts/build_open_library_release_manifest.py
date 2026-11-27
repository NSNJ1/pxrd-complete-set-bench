"""Rebuild the Git-index manifest for the v0.8 open-library release directory."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PANEL_RELATIVE = Path("evidence/open-library-precursor-genome-v0.8")
OUTPUT = REPO / PANEL_RELATIVE / "RELEASE_FILE_MANIFEST.json"


def main() -> int:
    completed = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--",
            PANEL_RELATIVE.as_posix(),
        ],
        cwd=REPO,
        capture_output=True,
        check=True,
    )
    paths = [
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item and Path(item.decode("utf-8")).name != OUTPUT.name
    ]
    entries = []
    for relative in sorted(paths):
        content = subprocess.check_output(
            ["git", "show", f":{relative}"],
            cwd=REPO,
        )
        entries.append(
            {
                "path": Path(relative).relative_to(PANEL_RELATIVE).as_posix(),
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    payload = {
        "release": "PXRD-CompleteSetBench Precursor Genome open-library panel",
        "version": "0.8.0",
        "date": "2026-11-27",
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
