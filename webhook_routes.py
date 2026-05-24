# -*- coding: utf-8 -*-
"""快麦 Webhook 路由（应用启动时尽早注册，避免被 /<path:path> 静态路由拦截）。"""
from __future__ import annotations

from flask import Flask, jsonify, request


def register_webhook_routes(app: Flask) -> None:
    @app.route("/api/webhook/kuaimai", methods=["GET", "POST"], endpoint="api_webhook_kuaimai")
    def api_webhook_kuaimai():
        if request.method == "GET":
            return jsonify(
                {
                    "success": True,
                    "msg": "kuaimai webhook ok",
                    "app": app.import_name,
                }
            )
        import kuaimai_webhook as kwh

        body = request.get_json(silent=True) or {}
        if not body and request.form:
            body = {k: request.form.get(k) for k in request.form.keys()}
        report = kwh.apply_webhook_payload(body)
        code = 200 if report.get("success", True) else 400
        return jsonify(report), code

    @app.route("/api/webhook/feishu", methods=["GET", "POST"], endpoint="api_webhook_feishu")
    def api_webhook_feishu():
        if request.method == "GET":
            import feishu_dify as fd

            return jsonify(
                {
                    "success": True,
                    "msg": "feishu-dify webhook",
                    "enabled": fd.is_enabled(),
                }
            )
        import feishu_dify as fd

        raw = request.get_data(cache=False) or b""
        hdrs = {}
        for key in (
            "X-Lark-Request-Timestamp",
            "X-Lark-Request-Nonce",
            "X-Lark-Signature",
        ):
            v = request.headers.get(key)
            if v:
                hdrs[key] = v
        body, code = fd.handle_webhook(raw, hdrs)
        return jsonify(body), code
