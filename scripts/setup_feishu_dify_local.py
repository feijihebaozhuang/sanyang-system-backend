#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键：写 .env、探活 Dify、启动本机桥接说明、ngrok 公网地址、飞书 URL 校验。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(_ROOT, ".env")

DEFAULT_FEISHU = {
    "app_id": os.getenv("FEISHU_APP_ID", ""),
    "app_secret": os.getenv("FEISHU_APP_SECRET", ""),
}
DEFAULT_DIFY_KEY = os.getenv("DIFY_API_KEY", "")


def _http_json(url, *, method="GET", headers=None, body=None, timeout=30):
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def feishu_tenant_token(app_id: str, app_secret: str) -> str:
    data = _http_json(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        method="POST",
        body={"app_id": app_id, "app_secret": app_secret},
    )
    if data.get("code") != 0:
        raise RuntimeError(data)
    return data["tenant_access_token"]


def test_dify(base: str, api_key: str) -> str:
    url = f"{base.rstrip('/')}/chat-messages"
    data = _http_json(
        url,
        method="POST",
        headers={"Authorization": f"Bearer {api_key}"},
        body={
            "query": "ping",
            "user": "setup-test",
            "response_mode": "blocking",
            "inputs": {},
        },
        timeout=120,
    )
    return (data.get("answer") or json.dumps(data, ensure_ascii=False))[:200]


def write_env(
    *,
    feishu: dict,
    dify_key: str,
    encrypt_key: str = "",
    verification_token: str = "",
) -> None:
    lines = []
    if os.path.isfile(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    keys = {
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", "local-dev"),
        "FLASK_SECRET_KEY": os.getenv("FLASK_SECRET_KEY", "local-dev-feishu-dify"),
        "FEISHU_DIFY_ENABLED": "true",
        "FEISHU_APP_ID": feishu["app_id"],
        "FEISHU_APP_SECRET": feishu["app_secret"],
        "FEISHU_VERIFICATION_TOKEN": verification_token,
        "FEISHU_ENCRYPT_KEY": encrypt_key,
        "DIFY_API_BASE": "http://127.0.0.1/v1",
        "DIFY_API_KEY": dify_key,
    }
    out: list[str] = []
    seen = set()
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in keys:
                out.append(f"{k}={keys[k]}")
                seen.add(k)
                continue
        out.append(line)
    for k, v in keys.items():
        if k not in seen:
            out.append(f"{k}={v}")
    text = "\n".join(out).rstrip() + "\n"
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"已写入 {ENV_PATH}")


def ngrok_public_url() -> str | None:
    try:
        data = _http_json("http://127.0.0.1:4040/api/tunnels", timeout=3)
    except Exception:
        return None
    for t in data.get("tunnels") or []:
        pub = t.get("public_url") or ""
        if pub.startswith("https://"):
            return pub.rstrip("/")
    return None


def feishu_url_verify(webhook_url: str, encrypt_key: str = "") -> bool:
    """模拟飞书 URL 校验（challenge）。"""
    import feishu_dify as fd

    payload = {"challenge": "test-challenge-ok", "type": "url_verification", "token": ""}
    raw = json.dumps(payload).encode("utf-8")
    body, code = fd.handle_webhook(raw, {})
    ok = code == 200 and body.get("challenge") == "test-challenge-ok"
    print(f"本机 URL 校验: {ok} {body}")
    return ok


def main() -> int:
    feishu = DEFAULT_FEISHU
    dify_key = os.getenv("DIFY_API_KEY", DEFAULT_DIFY_KEY)

    print("1) 写入 .env …")
    write_env(feishu=feishu, dify_key=dify_key)

    print("2) 检测 Dify API …")
    try:
        ans = test_dify("http://127.0.0.1/v1", dify_key)
        print(f"   Dify OK: {ans[:120]}")
    except Exception as e:
        print(f"   Dify 未就绪: {e}")
        print("   请在 WSL 执行: cd /opt/services/dify/docker && docker compose up -d")
        print("   并等待 docker-api-1 healthy 后重跑本脚本")

    print("3) ngrok 公网地址 …")
    pub = ngrok_public_url()
    if pub:
        wh = f"{pub}/api/webhook/feishu"
        print(f"   飞书事件订阅 URL: {wh}")
    else:
        print("   未检测到 ngrok（需另开终端: ngrok http 5099）")

    print("4) 飞书 tenant_token …")
    try:
        tok = feishu_tenant_token(feishu["app_id"], feishu["app_secret"])
        print(f"   飞书凭证 OK (token 前8位 {tok[:8]}…)")
    except Exception as e:
        print(f"   飞书凭证失败: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
