#!/usr/bin/env python3
"""Patch /home/admin/.hermes/config.yaml terminal section for 87 local ops."""
from __future__ import annotations

import re
import sys
from pathlib import Path

CFG = Path("/home/admin/.hermes/config.yaml")
TERMINAL_BLOCK = """terminal:
  backend: local
  shell: /bin/bash
  cwd: /www/feijihe/repo
  timeout: 180
"""


def main() -> int:
    if not CFG.is_file():
        print(f"missing {CFG}", file=sys.stderr)
        return 1
    raw = CFG.read_text(encoding="utf-8")
    bak = CFG.with_suffix(".yaml.bak.handoff")
    if not bak.is_file():
        bak.write_text(raw, encoding="utf-8")
    if re.search(r"^terminal:\s*$", raw, re.MULTILINE):
        new = re.sub(
            r"^terminal:\s*\n(?:^[ \t].*\n)*",
            TERMINAL_BLOCK + "\n",
            raw,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        stripped = re.sub(
            r"^terminal:\s*\n(?:^[ \t].*\n)*",
            "",
            raw,
            flags=re.MULTILINE,
        )
        new = stripped.rstrip() + "\n\n" + TERMINAL_BLOCK + "\n"
    # remove SSH leftovers
    new = re.sub(r"^\s*host:.*\n", "", new, flags=re.MULTILINE)
    new = re.sub(r"^\s*port:\s*22\s*\n", "", new, flags=re.MULTILINE)
    new = re.sub(r"^\s*user:\s*admin\s*\n", "", new, flags=re.MULTILINE)
    new = re.sub(r"^\s*password:.*\n", "", new, flags=re.MULTILINE)
    CFG.write_text(new, encoding="utf-8")
    print(f"patched {CFG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
