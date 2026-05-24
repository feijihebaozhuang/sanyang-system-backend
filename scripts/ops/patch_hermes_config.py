#!/usr/bin/env python3
"""Safely patch /home/admin/.hermes/config.yaml for 87 local ops + full shell tools."""
from __future__ import annotations

import argparse
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

TOOLSETS_BLOCK = """toolsets:
  - all
"""

PLATFORM_TOOLSETS_BLOCK = """platform_toolsets:
  feishu:
    - hermes-feishu
  lark:
    - hermes-feishu
"""

# Restore shell/file/code tools if someone disabled them globally.
_UNBLOCK_TOOLSETS = frozenset(
    {
        "terminal",
        "file",
        "code_execution",
        "web",
        "process",
        "execute_code",
    }
)


def _replace_top_level_block(text: str, key: str, block: str) -> str:
    pat = rf"^{re.escape(key)}:\s*\n(?:^[ \t].*\n)*"
    if re.search(pat, text, flags=re.MULTILINE):
        return re.sub(pat, block + "\n", text, count=1, flags=re.MULTILINE)
    return text.rstrip() + "\n\n" + block + "\n"


def _strip_disabled_toolsets(text: str) -> str:
    """Remove terminal/file/code_execution from agent.disabled_toolsets."""
    m = re.search(
        r"^(agent:\s*\n(?:^[ \t].*\n)*?^[ \t]+disabled_toolsets:\s*\n(?:^[ \t]+- .+\n)*)",
        text,
        flags=re.MULTILINE,
    )
    if not m:
        return text
    block = m.group(1)
    lines = block.splitlines(keepends=True)
    kept: list[str] = []
    for line in lines:
        item = re.match(r"^[ \t]+- (.+)\s*$", line)
        if item and item.group(1).strip().strip('"').strip("'") in _UNBLOCK_TOOLSETS:
            continue
        kept.append(line)
    new_block = "".join(kept)
    if re.search(r"^[ \t]+disabled_toolsets:\s*\n(?:^[ \t]+- .+\n)*$", new_block, re.MULTILINE):
        new_block = re.sub(
            r"^[ \t]+disabled_toolsets:\s*\n(?:^[ \t]+- .+\n)*",
            "",
            new_block,
            flags=re.MULTILINE,
        )
    return text[: m.start()] + new_block + text[m.end() :]


def _ensure_code_execution(text: str) -> str:
    if re.search(r"^code_execution:\s*$", text, re.MULTILINE):
        text = re.sub(
            r"(^code_execution:\s*\n(?:^[ \t].*\n)*)",
            lambda m: re.sub(
                r"^[ \t]+enabled:\s*false\s*\n",
                "",
                m.group(1),
                flags=re.MULTILINE,
            ),
            text,
            count=1,
            flags=re.MULTILINE,
        )
        return text
    return text.rstrip() + "\n\ncode_execution:\n  mode: project\n  timeout: 300\n"


def patch_config(raw: str) -> str:
    text = raw.replace("\r\n", "\n")
    text = re.sub(r"backend:\s*ssh\b", "backend: local", text)
    text = _replace_top_level_block(text, "terminal", TERMINAL_BLOCK.rstrip())
    text = _replace_top_level_block(text, "toolsets", TOOLSETS_BLOCK.rstrip())
    text = _replace_top_level_block(
        text, "platform_toolsets", PLATFORM_TOOLSETS_BLOCK.rstrip()
    )
    text = _strip_disabled_toolsets(text)
    text = _ensure_code_execution(text)
    if not text.endswith("\n"):
        text += "\n"
    return text


def show_sections(raw: str) -> None:
    for key in ("toolsets", "platform_toolsets", "terminal", "agent", "code_execution"):
        m = re.search(
            rf"^{re.escape(key)}:\s*\n(?:^[ \t].*\n)*",
            raw,
            flags=re.MULTILINE,
        )
        print(f"--- {key} ---")
        print(m.group(0).rstrip() if m else "(missing)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch Hermes config for 87 shell tools")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print tool-related sections only; do not write",
    )
    args = parser.parse_args()
    if not CFG.is_file():
        print(f"missing {CFG}", file=sys.stderr)
        return 1
    raw = CFG.read_text(encoding="utf-8")
    if args.check:
        show_sections(raw)
        return 0
    bak = CFG.with_suffix(".yaml.bak.toolsfix")
    if not bak.is_file():
        bak.write_text(raw, encoding="utf-8")
    new = patch_config(raw)
    CFG.write_text(new, encoding="utf-8")
    print(f"patched {CFG}")
    show_sections(new)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
