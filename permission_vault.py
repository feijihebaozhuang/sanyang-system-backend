# -*- coding: utf-8 -*-
"""
权限配置保险库：permission_data 放在独立服务器，业务机只读拉取。

环境变量（写在 stable/.env，勿提交 Git）：
  PERMISSION_VAULT_URL       只读 GET，返回 JSON 或 {"permission_data":{...}}
  PERMISSION_VAULT_TOKEN     可选，Bearer 或 X-Config-Token
  PERMISSION_VAULT_WRITE_URL 可选，仅配置机 POST 写入；业务机不配置则禁止改权限 JSON
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any


def vault_enabled() -> bool:
    if (os.getenv("PERMISSION_VAULT_OFF") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return False
    return bool((os.getenv("PERMISSION_VAULT_URL") or "").strip())


def vault_readonly_on_app() -> bool:
    """业务服务器：有 VAULT_URL 且未配置 WRITE_URL → 禁止本机/页面写入 permission_data。"""
    if not vault_enabled():
        return False
    return not (os.getenv("PERMISSION_VAULT_WRITE_URL") or "").strip()


def _request_headers() -> dict[str, str]:
    token = (os.getenv("PERMISSION_VAULT_TOKEN") or "").strip()
    h: dict[str, str] = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
        h["X-Config-Token"] = token
    return h


def _write_headers() -> dict[str, str]:
    """156 permission_vault POST 认 X-Vault-Token；同时保留 Bearer 兼容其它部署。"""
    h = _request_headers()
    token = (os.getenv("PERMISSION_VAULT_TOKEN") or "").strip()
    if token:
        h["X-Vault-Token"] = token
    h["Content-Type"] = "application/json"
    return h


def _parse_permission_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict) and isinstance(raw.get("permission_data"), dict):
        return raw["permission_data"]
    if isinstance(raw, dict):
        return raw
    return {}


def _get_urlopen_context(url: str) -> ssl.SSLContext | None:
    """Only wrap SSL for HTTPS URLs; HTTP v3/v4 plain-text needs no context."""
    if url.startswith("https://"):
        return ssl.create_default_context()
    return None


def fetch_permission_overlay(timeout: float = 10.0) -> dict[str, Any]:
    url = (os.getenv("PERMISSION_VAULT_URL") or "").strip()
    if not url:
        return {}
    req = urllib.request.Request(url, headers=_request_headers(), method="GET")
    ctx = _get_urlopen_context(url)
    kwargs: dict[str, Any] = {"timeout": timeout}
    if ctx is not None:
        kwargs["context"] = ctx
    with urllib.request.urlopen(req, **kwargs) as resp:  # type: ignore[arg-type]
        body = resp.read().decode("utf-8")
    return _parse_permission_payload(json.loads(body))


def push_permission_overlay(
    permission_data: dict[str, Any],
    *,
    keys: frozenset[str] | None = None,
    timeout: float = 15.0,
) -> bool:
    """仅配置服务器调用（PERMISSION_VAULT_WRITE_URL 指向保险库 POST 接口）。"""
    write_url = (os.getenv("PERMISSION_VAULT_WRITE_URL") or "").strip()
    if not write_url:
        return False
    import config_json as cfg

    kset = keys or cfg.PERMISSION_JSON_KEYS
    patch = {k: permission_data[k] for k in kset if k in permission_data}
    payload = json.dumps({"permission_data": patch}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        write_url, data=payload, headers=_write_headers(), method="POST"
    )
    ctx = _get_urlopen_context(write_url)
    kwargs: dict[str, Any] = {"timeout": timeout}
    if ctx is not None:
        kwargs["context"] = ctx
    try:
        with urllib.request.urlopen(req, **kwargs) as resp:  # type: ignore[arg-type]
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        print(f"[permission_vault] 写入失败 HTTP {e.code}: {e.read()[:500]}")
        return False
    except OSError as e:
        print(f"[permission_vault] 写入失败: {e}")
        return False
