#!/usr/bin/env python3
"""Replace machine-local input paths in score JSON with run-relative paths."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sanitize(value: object) -> object:
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key == "path" and isinstance(item, str):
                path = Path(item)
                result[key] = Path(path.parent.name, path.name).as_posix()
            else:
                result[key] = sanitize(item)
        return result
    return value


def main() -> int:
    changed = []
    for directory in (ROOT / "scores_v8", ROOT / "sensitivity_v8"):
        for path in sorted(directory.glob("*.json")):
            original = json.loads(path.read_text(encoding="utf-8"))
            clean = sanitize(original)
            path.write_text(
                json.dumps(clean, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            changed.append(str(path.relative_to(ROOT)))
    print(f"sanitized {len(changed)} score JSON files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
