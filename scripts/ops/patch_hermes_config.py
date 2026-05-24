#!/usr/bin/env python3
"""Safely patch /home/admin/.hermes/config.yaml + env for 87 shell tools."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CFG = Path("/home/admin/.hermes/config.yaml")
ENV_FILES = (Path("/home/admin/.hermes/env"), Path("/home/admin/.hermes/.env"))

TERMINAL_BLOCK = """terminal:
  backend: local
  shell: /bin/bash
  cwd: /www/feijihe/repo
  timeout: 180
"""

TOOLSETS_BLOCK = """toolsets:
  - all
"""

# 显式列出飞书通道工具集（避免 hermes tools 曾勾选「安全子集」后 composite 解析仍缺 terminal）
FEISHU_TOOLSETS = (
    "web",
    "terminal",
    "file",
    "code_execution",
    "browser",
    "vision",
    "skills",
    "todo",
    "memory",
    "session_search",
    "clarify",
    "delegation",
    "cronjob",
    "messaging",
    "tts",
)

PLATFORM_TOOLSETS_BLOCK = "platform_toolsets:\n" + "\n".join(
    f"  {plat}:\n" + "\n".join(f"    - {ts}" for ts in FEISHU_TOOLSETS)
    for plat in ("feishu", "lark")
)

TERMINAL_ENV_SET = {
    "TERMINAL_ENV": "local",
    "TERMINAL_CWD": "/www/feijihe/repo",
    "TERMINAL_TIMEOUT": "180",
}

_UNBLOCK_TOOLSETS = frozenset(
    {
        "terminal",
        "file",
        "code_execution",
        "web",
        "process",
        "execute_code",
        "safe",
    }
)


def _remove_top_level_blocks(text: str, keys: tuple[str, ...]) -> str:
    for key in keys:
        text = re.sub(
            rf"^{re.escape(key)}:\s*\n(?:^[ \t].*\n)*",
            "",
            text,
            flags=re.MULTILINE,
        )
    return text


def _remove_root_orphan_yaml_items(text: str) -> str:
    """Remove stray list items left by broken sed (e.g. root-level `- hermes-cli`)."""
    return re.sub(
        r"^-\s+(?:hermes-cli|hermes-feishu|all|\*)\s*\n",
        "",
        text,
        flags=re.MULTILINE,
    )


def _strip_disabled_toolsets(text: str) -> str:
    m = re.search(
        r"^(agent:\s*\n(?:^[ \t].*\n)*?^[ \t]+disabled_toolsets:\s*\n(?:^[ \t]+- .+\n)*)",
        text,
        flags=re.MULTILINE,
    )
    if not m:
        return text
    block = m.group(1)
    kept: list[str] = []
    for line in block.splitlines(keepends=True):
        item = re.match(r"^[ \t]+- (.+)\s*$", line)
        if item and item.group(1).strip().strip('"').strip("'") in _UNBLOCK_TOOLSETS:
            continue
        kept.append(line)
    new_block = "".join(kept)
    if re.search(
        r"^[ \t]+disabled_toolsets:\s*\n(?:^[ \t]+- .+\n)*$",
        new_block,
        re.MULTILINE,
    ):
        new_block = re.sub(
            r"^[ \t]+disabled_toolsets:\s*\n(?:^[ \t]+- .+\n)*",
            "",
            new_block,
            flags=re.MULTILINE,
        )
    return text[: m.start()] + new_block + text[m.end() :]


def _ensure_code_execution(text: str) -> str:
    if re.search(r"^code_execution:\s*$", text, re.MULTILINE):
        return re.sub(
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
    return text.rstrip() + "\n\ncode_execution:\n  mode: project\n  timeout: 300\n"


def patch_config(raw: str) -> str:
    text = raw.replace("\r\n", "\n")
    text = re.sub(r"backend:\s*ssh\b", "backend: local", text)
    text = _remove_root_orphan_yaml_items(text)
    text = _remove_top_level_blocks(text, ("terminal", "toolsets", "platform_toolsets"))
    text = _strip_disabled_toolsets(text)
    text = _ensure_code_execution(text)
    text = text.rstrip() + "\n\n"
    text += TERMINAL_BLOCK + "\n" + TOOLSETS_BLOCK + "\n" + PLATFORM_TOOLSETS_BLOCK + "\n"
    if not text.endswith("\n"):
        text += "\n"
    return text


def patch_env_file(path: Path) -> bool:
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            out.append(line)
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key in TERMINAL_ENV_SET:
            continue
        if key == "TERMINAL_ENV" and val.strip().lower() != "local":
            continue
        if key.startswith("TERMINAL_SSH_"):
            continue
        out.append(line)
        seen.add(key)
    for key, val in TERMINAL_ENV_SET.items():
        if key not in seen:
            out.append(f"{key}={val}")
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return True


def patch_env() -> list[Path]:
    touched: list[Path] = []
    for path in ENV_FILES:
        if patch_env_file(path):
            touched.append(path)
    return touched


def show_sections(raw: str) -> None:
    for key in ("toolsets", "platform_toolsets", "terminal", "agent", "code_execution"):
        m = re.search(
            rf"^{re.escape(key)}:\s*\n(?:^[ \t].*\n)*",
            raw,
            flags=re.MULTILINE,
        )
        print(f"--- {key} ---")
        print(m.group(0).rstrip() if m else "(missing)")


def show_env() -> None:
    for path in ENV_FILES:
        print(f"--- env {path} ---")
        if not path.is_file():
            print("(missing)")
            continue
        for key in ("TERMINAL_ENV", "TERMINAL_CWD", "TERMINAL_SSH_HOST", "TERMINAL_SSH_USER"):
            m = re.search(rf"^{re.escape(key)}=(.*)$", path.read_text(encoding="utf-8"), re.MULTILINE)
            print(f"{key}={m.group(1) if m else '(unset)'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch Hermes config/env for 87 shell tools")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print tool-related sections + TERMINAL_* env; do not write",
    )
    args = parser.parse_args()
    if not CFG.is_file():
        print(f"missing {CFG}", file=sys.stderr)
        return 1
    raw = CFG.read_text(encoding="utf-8")
    if args.check:
        show_sections(raw)
        show_env()
        return 0
    bak = CFG.with_suffix(".yaml.bak.toolsfix2")
    if not bak.is_file():
        bak.write_text(raw, encoding="utf-8")
    new = patch_config(raw)
    CFG.write_text(new, encoding="utf-8")
    env_touched = patch_env()
    print(f"patched {CFG}")
    if env_touched:
        print("patched env:", ", ".join(str(p) for p in env_touched))
    else:
        print("WARN: no hermes env file found — create /home/admin/.hermes/env")
    show_sections(new)
    show_env()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
