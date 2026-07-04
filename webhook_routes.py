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

    @app.route("/api/internal/self-repair", methods=["GET", "POST"])
    def api_internal_self_repair():
        """小马哥本机自救：修 Hermes、关 vault、拉 Gitee 代码。仅 127.0.0.1 或带令牌。"""
        try:
            import agent_self_repair as asr
        except ImportError:
            return jsonify({"success": False, "error": "自修复模块未安装"}), 503

        if request.method == "GET":
            return jsonify(
                {
                    "success": True,
                    "msg": "POST with X-Ops-Token to run repair",
                    "token_hint": "OPS_SELF_REPAIR_TOKEN or FLASK_SECRET_KEY前32位",
                    "gitee_token_set": bool(asr._gitee_token()),
                }
            )
        remote = (request.remote_addr or "").strip()
        token = (request.headers.get("X-Ops-Token") or "").strip()
        if remote not in ("127.0.0.1", "::1") and token != asr.repair_token():
            return jsonify({"success": False, "error": "需要本机访问或正确 X-Ops-Token"}), 403
        restart = request.args.get("restart", "1") not in ("0", "false", "no")
        report = asr.repair_all(restart=restart)
        return jsonify({"success": True, "report": report})
