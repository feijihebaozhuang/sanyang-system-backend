# -*- coding: utf-8 -*-
"""
87 应用机启动时自动把 Hermes 从 SSH 模式改成本机 local，避免工具链卡死。
deploy 同步 .py 后重启 sanyang-cs / sanyang-production 即会执行。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_HERMES_CFG = Path("/home/admin/.hermes/config.yaml")
_DONE = False


def _strip_ssh_lines(text: str) -> str:
    drop = re.compile(
        r"^\s*(host:|port:\s*22|user:\s*admin|password:)\s*.*$",
        re.MULTILINE,
    )
    return drop.sub("", text)


def auto_fix_hermes_local_backend() -> bool:
    """backend: ssh → local；去掉 SSH 段。成功改文件返回 True。"""
    global _DONE
    if _DONE:
        return False
    _DONE = True
    if not _HERMES_CFG.is_file():
        return False
    try:
        raw = _HERMES_CFG.read_text(encoding="utf-8")
    except OSError as e:
        print(f"[hermes_boot_fix] 读配置失败: {e}")
        return False
    if "backend: ssh" not in raw and "backend:ssh" not in raw.replace(" ", ""):
        return False
    fixed = raw.replace("backend: ssh", "backend: local")
    fixed = _strip_ssh_lines(fixed)
    try:
        bak = _HERMES_CFG.with_suffix(".yaml.bak.autofix")
        if not bak.is_file():
            bak.write_text(raw, encoding="utf-8")
        _HERMES_CFG.write_text(fixed, encoding="utf-8")
        print("[hermes_boot_fix] Hermes config → backend: local")
    except OSError as e:
        print(f"[hermes_boot_fix] 写配置失败: {e}")
        return False
    try:
        subprocess.run(
            ["sudo", "-n", "systemctl", "restart", "hermes-agent"],
            check=False,
            capture_output=True,
            timeout=15,
        )
    except OSError:
        pass
    return True
