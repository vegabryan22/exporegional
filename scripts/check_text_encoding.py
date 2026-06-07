#!/usr/bin/env python3
"""Fail when Spanish UI text is saved with broken UTF-8/mojibake."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ["app", "scripts"]
SCAN_SUFFIXES = {".py", ".html", ".css", ".js", ".md", ".txt", ".yml", ".yaml", ".json"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "uploads"}
MOJIBAKE_MARKERS = ("\u00c3", "\u00c2", "\ufffd", "\ufeff")
SPANISH_LETTERS = "A-Za-z\u00c1\u00c9\u00cd\u00d3\u00da\u00dc\u00d1\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1"
BROKEN_QUESTION_RE = re.compile(rf"(?:\b[{SPANISH_LETTERS}]+\?[{SPANISH_LETTERS}]+|\?[{SPANISH_LETTERS}]{{2,}})")


def iter_files() -> list[Path]:
    files: list[Path] = []
    for dirname in SCAN_DIRS:
        base = ROOT / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in SCAN_SUFFIXES:
                files.append(path)
    return files


def line_has_allowed_question(line: str, match: re.Match[str]) -> bool:
    # Normal Spanish questions use the inverted opener. Those are valid.
    start = match.start()
    return start > 0 and line[start - 1] == "\u00bf"


def main() -> int:
    errors: list[str] = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{path.relative_to(ROOT)}: not valid UTF-8: {exc}")
            continue

        for marker in MOJIBAKE_MARKERS:
            if marker in text:
                errors.append(f"{path.relative_to(ROOT)}: contains mojibake marker {marker.encode('unicode_escape').decode()}")

        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in BROKEN_QUESTION_RE.finditer(line):
                if line_has_allowed_question(line, match):
                    continue
                errors.append(f"{path.relative_to(ROOT)}:{line_no}: possible broken accent: {line.strip()}")

    if errors:
        print("ERROR: broken text encoding detected:\n")
        for item in errors:
            print(f"- {item}")
        return 1

    print("OK: UTF-8 text without mojibake detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
