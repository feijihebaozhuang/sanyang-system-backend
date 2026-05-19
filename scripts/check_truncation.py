#!/usr/bin/env python3
"""扫描常见代码截断（未闭合引号、半截标识符等）。"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ["km_api.py", "app_cs.py", "app_production.py"]
PATTERNS = [
    (re.compile(r"os\.get\.\.\."), "os.get... 截断"),
    (re.compile(r"mv\.get\('name\b(?!')"), "mv.get('name 缺闭合引号"),
    (re.compile(r"jsonify\(paylo\b(?!ad)"), "jsonify(paylo 截断"),
    (re.compile(r"os\.getenv\([^)]*\.\.\."), "getenv 截断"),
    (re.compile(r"\.get\('[^']*$"), "行末未闭合单引号 .get('"),
]


def main() -> int:
    failed = False
    for name in TARGETS:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        try:
            ast.parse(text, filename=name)
        except SyntaxError as e:
            print(f"[SYNTAX] {name}:{e.lineno}: {e.msg}")
            failed = True
        for i, line in enumerate(text.splitlines(), 1):
            for rx, msg in PATTERNS:
                if rx.search(line):
                    print(f"[PATTERN] {name}:{i}: {msg} -> {line[:100]!r}")
                    failed = True
    if failed:
        return 1
    print("OK:", ", ".join(TARGETS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
