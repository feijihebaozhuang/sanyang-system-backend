#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署前：编译检查仓库内全部 .py 文件（排除 venv/backups）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"venv", "__pycache__", ".git", "backups", "node_modules"}


def main() -> int:
    failed: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(ROOT)
        try:
            src = path.read_text(encoding="utf-8")
            compile(src, str(rel), "exec")
        except SyntaxError as e:
            failed.append(f"{rel}:{e.lineno}: {e.msg}")
        except OSError as e:
            failed.append(f"{rel}: {e}")

    if failed:
        print("COMPILE FAILED:")
        for line in failed:
            print(" ", line)
        return 1
    n = sum(1 for p in ROOT.rglob("*.py") if not any(x in SKIP_DIRS for x in p.parts))
    print(f"OK: {n} Python files compiled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
