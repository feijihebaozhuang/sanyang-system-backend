# -*- coding: utf-8 -*-
"""
87 小马哥（Hermes）自我修复：不依赖 SSH 跳板、不依赖老板本地操作。
- 网站进程启动时自动跑一遍
- POST /api/internal/self-repair（本机 curl，令牌见 stable/.env）
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import hermes_boot_fix as _hermes

_ROOT = Path(__file__).resolve().parent
_STABLE = Path(os.environ.get("STABLE_DIR", _ROOT))
_ENV = _STABLE / ".env"
_REPO = Path("/www/feijihe/repo")
_HERMES_ENV = Path("/home/admin/.hermes/env")


def _load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _gitee_token() -> str:
    for p in (_ENV, _HERMES_ENV):
        t = _load_dotenv(p).get("GITEE_TOKEN", "")
        if t:
            return t
    return (os.getenv("GITEE_TOKEN") or "").strip()


def repair_token() -> str:
    env = _load_dotenv(_ENV)
    t = (env.get("OPS_SELF_REPAIR_TOKEN") or "").strip()
    if t:
        return t
    sk = (env.get("FLASK_SECRET_KEY") or os.getenv("FLASK_SECRET_KEY") or "").strip()
    return sk[:32] if sk else "sanyang-self-repair"


def repair_hermes() -> dict[str, Any]:
    ok = _hermes.auto_fix_hermes_local_backend()
    return {"hermes_local": ok, "config": str(_hermes._HERMES_CFG)}


def repair_vault_off() -> dict[str, Any]:
    """暂停 156 vault 覆盖，权限回 stable/data.json。"""
    if not _ENV.is_file():
        return {"vault_off": False, "reason": "no .env"}
    raw = _ENV.read_text(encoding="utf-8")
    if re.search(r"^PERMISSION_VAULT_OFF=1\s*$", raw, re.MULTILINE):
        return {"vault_off": True, "already": True}
    lines = [
        ln
        for ln in raw.splitlines()
        if not ln.startswith("PERMISSION_VAULT_")
    ]
    lines.extend(
        [
            "",
            f"# agent_self_repair {__import__('datetime').date.today()}",
            "PERMISSION_VAULT_OFF=1",
        ]
    )
    _ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"vault_off": True, "path": str(_ENV)}


def repair_sync_code() -> dict[str, Any]:
    token = _gitee_token()
    if not token:
        return {"sync": False, "reason": "无 GITEE_TOKEN（请在 .env 或 /home/admin/.hermes/env 配置）"}
    url = (
        "https://gitee.com/api/v5/repos/feijihesanyan/sanyang-system/"
        f"tarball/main?access_token={token}"
    )
    tmp = Path(tempfile.mkdtemp(prefix="sanyang-sync-"))
    try:
        arc = tmp / "repo.tar.gz"
        urllib.request.urlretrieve(url, arc)
        with tarfile.open(arc, "r:gz") as tf:
            tf.extractall(tmp)
        sub = next(p for p in tmp.iterdir() if p.is_dir())
        _REPO.mkdir(parents=True, exist_ok=True)
        if shutil.which("rsync"):
            subprocess.run(
                [
                    "rsync",
                    "-a",
                    "--include=*.py",
                    "--include=requirements.txt",
                    "--include=scripts/",
                    "--include=scripts/**",
                    "--exclude=*",
                    f"{sub}/",
                    f"{_STABLE}/",
                ],
                check=False,
                timeout=120,
            )
        else:
            for py in sub.rglob("*.py"):
                rel = py.relative_to(sub)
                dest = _STABLE / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(py, dest)
        return {"sync": True, "stable": str(_STABLE)}
    except Exception as e:
        return {"sync": False, "error": str(e)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def repair_services() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for svc in ("sanyang-cs", "sanyang-production", "hermes-agent"):
        r = subprocess.run(
            ["sudo", "-n", "systemctl", "restart", svc],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out[svc] = r.returncode == 0
    return out


def repair_all(*, restart: bool = False) -> dict[str, Any]:
    result = {
        "hermes": repair_hermes(),
        "vault": repair_vault_off(),
        "code": repair_sync_code(),
    }
    if restart:
        result["services"] = repair_services()
    return result


def run_boot_repair() -> None:
    """gunicorn 启动时：修 Hermes + 关 vault；不自动 restart 自身。"""
    try:
        repair_hermes()
        repair_vault_off()
    except Exception as e:
        print(f"[agent_self_repair] boot: {e}")
