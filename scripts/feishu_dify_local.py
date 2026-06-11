#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本机调试：仅启动飞书↔Dify Webhook（Dify 在 WSL 时用）。

用法（PowerShell，项目根目录）:
  $env:MYSQL_PASSWORD="local"; $env:FEISHU_DIFY_ENABLED="true"
  $env:DIFY_API_BASE="http://127.0.0.1/v1"; $env:DIFY_API_KEY="app-xxx"
  # … 其余 FEISHU_* 见 .env.example
  python scripts/feishu_dify_local.py

飞书回调须公网 HTTPS：用 ngrok / cloudflared 把本机 5099 暴露出去，例如:
  ngrok http 5099
  飞书事件订阅 URL: https://xxxx.ngrok-free.app/api/webhook/feishu
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("MYSQL_PASSWORD", "local-dev")
os.environ.setdefault("FLASK_SECRET_KEY", "local-dev-feishu-dify")

from flask import Flask, jsonify, request

import feishu_dify as fd
from settings import get_feishu_dify_config
from webhook_routes import register_webhook_routes

app = Flask(__name__)
register_webhook_routes(app)

PORT = int(os.getenv("FEISHU_DIFY_LOCAL_PORT", "5099"))


@app.route("/")
def index():
    return jsonify(
        {
            "service": "feishu-dify-local",
            "enabled": fd.is_enabled(),
            "webhook": "/api/webhook/feishu",
            "dify_api_base": get_feishu_dify_config().get("dify_api_base"),
        }
    )


if __name__ == "__main__":
    print(f"飞书-Dify 本机桥接 http://127.0.0.1:{PORT}/api/webhook/feishu")
    print(f"enabled={fd.is_enabled()}  dify={get_feishu_dify_config().get('dify_api_base')}")
    if not fd.is_enabled():
        print("请在环境变量或 .env 中配置 FEISHU_DIFY_ENABLED 与密钥，见 docs/FEISHU_DIFY.md")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
