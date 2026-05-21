#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立配置机示例：托管 permission_data.json（只读 GET + 带 Token 的 POST）。

用法（在配置机上，非业务机）：
  export PERMISSION_VAULT_TOKEN='你的长随机串'
  export PERMISSION_DATA_FILE=/opt/sanyang-config/permission_data.json
  python3 permission_vault_server.example.py

业务机 .env 只配：
  PERMISSION_VAULT_URL=http://配置机IP:9443/permission_data.json
  PERMISSION_VAULT_TOKEN=同上
  不要配 PERMISSION_VAULT_WRITE_URL
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOST = os.getenv("PERMISSION_VAULT_BIND", "0.0.0.0")
PORT = int(os.getenv("PERMISSION_VAULT_PORT", "9443"))
DATA_FILE = Path(
    os.getenv("PERMISSION_VAULT_DATA_FILE", "/opt/sanyang-config/permission_data.json")
)
TOKEN = (os.getenv("PERMISSION_VAULT_TOKEN") or "").strip()


def _check_token(handler: BaseHTTPRequestHandler) -> bool:
    if not TOKEN:
        return True
    auth = handler.headers.get("Authorization", "")
    if auth == f"Bearer {TOKEN}":
        return True
    if handler.headers.get("X-Config-Token") == TOKEN:
        return True
    return False


def _load() -> dict:
    if not DATA_FILE.is_file():
        return {}
    with DATA_FILE.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "permission_data" in raw:
        return raw["permission_data"]
    return raw if isinstance(raw, dict) else {}


def _save(patch: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = _load()
    for k, v in patch.items():
        existing[k] = v
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[vault] {self.address_string()} {fmt % args}")

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.rstrip("/") not in ("/permission_data.json", "/permission_data"):
            self._json(404, {"error": "not found"})
            return
        if not _check_token(self):
            self._json(401, {"error": "unauthorized"})
            return
        self._json(200, {"permission_data": _load()})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/permission_data":
            self._json(404, {"error": "not found"})
            return
        if not _check_token(self):
            self._json(401, {"error": "unauthorized"})
            return
        n = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        patch = body.get("permission_data") if isinstance(body, dict) else body
        if not isinstance(patch, dict):
            self._json(400, {"error": "need permission_data object"})
            return
        _save(patch)
        self._json(200, {"success": True})


def main() -> None:
    print(f"监听 {HOST}:{PORT} 文件 {DATA_FILE} token={'set' if TOKEN else 'NONE'}")
    HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
