#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三羊客户下单系统 — 3003 网页后台
与 3001/3002 独立进程，不修改现有客服/生产端。
"""
from __future__ import annotations

import hashlib
import os
from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

from settings import FLASK_SECRET_KEY

app = Flask(__name__, static_folder=".")
app.secret_key = FLASK_SECRET_KEY
CORS(app, supports_credentials=True)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=31)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "").lower() in (
    "1", "true", "yes"
)

co_store = None

_tables_bootstrapped = False


def _bootstrap_tables():
    global _tables_bootstrapped
    if _tables_bootstrapped:
        return
    import customer_order_store as _co

    global co_store
    co_store = _co
    _co.ensure_tables()
    _tables_bootstrapped = True


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "service": "customer-order", "port": 3003})


@app.before_request
def _ensure_co_tables():
    if request.endpoint == "health":
        return None
    _bootstrap_tables()


def _auth_token_for(username: str) -> str:
    return hashlib.sha256(f"{FLASK_SECRET_KEY}:{username}".encode()).hexdigest()[:32]


def resolve_login_user() -> dict | None:
    username = session.get("username")
    if username:
        user = co_store.get_admin_by_username(username)
        if user and user.get("enabled"):
            return user
    hdr_user = (request.headers.get("X-Sanyang-User") or "").strip()
    hdr_tok = (request.headers.get("X-Sanyang-Token") or "").strip()
    if hdr_user and hdr_tok and hdr_tok == _auth_token_for(hdr_user):
        user = co_store.get_admin_by_username(hdr_user)
        if user and user.get("enabled"):
            return user
    return None


def require_login():
    if not resolve_login_user():
        return jsonify({"success": False, "error": "未登录", "code": 401}), 401
    return None


def require_admin():
    user = resolve_login_user()
    if not user:
        return jsonify({"success": False, "error": "未登录", "code": 401}), 401
    if user.get("role") != "admin":
        return jsonify({"success": False, "error": "无权限", "code": 403}), 403
    return None


def _user_payload(user: dict) -> dict:
    username = user.get("username") or ""
    return {
        "username": username,
        "display_name": user.get("display_name") or username,
        "role": user.get("role") or "viewer",
        "auth_token": _auth_token_for(username),
    }


@app.route("/")
def index():
    return send_from_directory(".", "index_customer_order.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return jsonify({"success": False, "message": "请输入账号和密码"})
    user = co_store.get_admin_by_username(username)
    if not user or not user.get("enabled"):
        return jsonify({"success": False, "message": "账号或密码错误"})
    if user.get("password_hash") != co_store.password_hash(password):
        return jsonify({"success": False, "message": "账号或密码错误"})
    session.permanent = True
    session["username"] = username
    session.modified = True
    return jsonify({"success": True, "user": _user_payload(user)})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/me")
def me():
    user = resolve_login_user()
    if not user:
        return jsonify({"success": False, "error": "未登录", "code": 401}), 401
    return jsonify({"success": True, "user": _user_payload(user)})


@app.route("/api/dashboard")
def dashboard():
    err = require_login()
    if err:
        return err
    return jsonify({"success": True, "stats": co_store.dashboard_stats()})


# ---------- 产品目录 ----------
@app.route("/api/categories")
def api_categories():
    err = require_login()
    if err:
        return err
    include_disabled = request.args.get("all") == "1"
    return jsonify({"success": True, "items": co_store.list_categories(include_disabled=include_disabled)})


@app.route("/api/categories/save", methods=["POST"])
def api_categories_save():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        item = co_store.upsert_category(data)
        return jsonify({"success": True, "item": item})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------- 客服员工 ----------
@app.route("/api/cs_staff")
def api_cs_staff():
    err = require_login()
    if err:
        return err
    include_disabled = request.args.get("all") == "1"
    return jsonify({"success": True, "items": co_store.list_cs_staff(include_disabled=include_disabled)})


@app.route("/api/cs_staff/save", methods=["POST"])
def api_cs_staff_save():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        item = co_store.upsert_cs_staff(data)
        return jsonify({"success": True, "item": item})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------- 客户 ----------
@app.route("/api/customers")
def api_customers():
    err = require_login()
    if err:
        return err
    assigned_cs_id = request.args.get("assigned_cs_id")
    keyword = (request.args.get("keyword") or "").strip()
    status = (request.args.get("status") or "").strip()
    limit = min(int(request.args.get("limit") or 200), 500)
    offset = max(int(request.args.get("offset") or 0), 0)
    items, total = co_store.list_customers(
        assigned_cs_id=int(assigned_cs_id) if assigned_cs_id else None,
        keyword=keyword,
        status=status,
        limit=limit,
        offset=offset,
    )
    return jsonify({"success": True, "items": items, "total": total})


@app.route("/api/customers/save", methods=["POST"])
def api_customers_save():
    err = require_login()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        item = co_store.upsert_customer(data)
        return jsonify({"success": True, "item": item})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------- 订单 ----------
@app.route("/api/orders")
def api_orders():
    err = require_login()
    if err:
        return err
    status = (request.args.get("status") or "").strip()
    customer_id = request.args.get("customer_id")
    cs_staff_id = request.args.get("cs_staff_id")
    keyword = (request.args.get("keyword") or "").strip()
    limit = min(int(request.args.get("limit") or 100), 500)
    offset = max(int(request.args.get("offset") or 0), 0)
    items, total = co_store.list_orders(
        status=status,
        customer_id=int(customer_id) if customer_id else None,
        cs_staff_id=int(cs_staff_id) if cs_staff_id else None,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )
    return jsonify({"success": True, "items": items, "total": total})


@app.route("/api/orders/<int:order_id>")
def api_order_detail(order_id: int):
    err = require_login()
    if err:
        return err
    item = co_store.get_order(order_id)
    if not item:
        return jsonify({"success": False, "error": "订单不存在"}), 404
    return jsonify({"success": True, "item": item})


@app.route("/api/orders/save", methods=["POST"])
def api_orders_save():
    err = require_login()
    if err:
        return err
    user = resolve_login_user()
    data = request.get_json(silent=True) or {}
    try:
        item = co_store.upsert_order(data, created_by=user.get("username") if user else "admin")
        return jsonify({"success": True, "item": item})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/sku/match", methods=["POST"])
def api_sku_match():
    err = require_login()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    match = co_store.lookup_sku_match(
        (data.get("product_category_code") or data.get("product_type") or "").strip(),
        float(data.get("length") or 0),
        float(data.get("width") or 0),
        float(data.get("height") or 0),
        (data.get("material") or "").strip(),
        (data.get("dim_kind") or "").strip(),
    )
    return jsonify({"success": True, "match": match, "matched": bool(match)})


# ---------- 权限管理 ----------
@app.route("/api/admin_users")
def api_admin_users():
    err = require_admin()
    if err:
        return err
    return jsonify({"success": True, "items": co_store.list_admin_users()})


@app.route("/api/admin_users/save", methods=["POST"])
def api_admin_users_save():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        item = co_store.upsert_admin_user(data)
        safe = {k: v for k, v in item.items() if k != "password_hash"}
        return jsonify({"success": True, "item": safe})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------- 员工 / 功能权限（与 3001/3002 共用 MySQL + data.json） ----------
import employee_perm_store as emp_store

PERM_FEATURES = emp_store.PERM_FEATURES


@app.route("/api/perm/data")
def api_perm_data():
    err = require_admin()
    if err:
        return err
    bundle = emp_store.load_permission_bundle()
    return jsonify({"success": True, "data": bundle, "features": PERM_FEATURES})


@app.route("/api/perm/save", methods=["POST"])
def api_perm_save():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    payload = data.get("data") if isinstance(data.get("data"), dict) else data
    try:
        result = emp_store.save_permission_bundle(payload)
        return jsonify({"success": True, **result})
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/perm/employees/save", methods=["POST"])
def api_perm_employee_save():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        item = emp_store.upsert_employee(
            data.get("name") or "",
            data.get("position") or "",
            enabled=bool(data.get("enabled", True)),
        )
        return jsonify({"success": True, "item": item})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/perm/employees/delete", methods=["POST"])
def api_perm_employee_delete():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "name 必填"}), 400
    emp_store.delete_employee(name)
    return jsonify({"success": True})


@app.route("/api/perm/users")
def api_perm_users():
    err = require_admin()
    if err:
        return err
    return jsonify({"success": True, "items": emp_store.list_users()})


@app.route("/api/perm/users/save", methods=["POST"])
def api_perm_users_save():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        item = emp_store.upsert_user(
            data.get("username") or "",
            password=(data.get("password") or "").strip(),
            display_name=(data.get("display_name") or "").strip(),
            role=(data.get("role") or "员工").strip(),
            employee_name=(data.get("employee_name") or "").strip(),
            enabled=bool(data.get("enabled", True)),
        )
        return jsonify({"success": True, "item": item})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/admin/sync_km_sku/status")
def api_sync_km_sku_status():
    err = require_admin()
    if err:
        return err
    import km_sku_map_store as kms
    from pathlib import Path

    ck_path = Path(__file__).resolve().parent / "data" / "km_sku_sync_checkpoint.json"
    ck = {}
    if ck_path.is_file():
        try:
            import json

            ck = json.loads(ck_path.read_text(encoding="utf-8"))
        except Exception:
            ck = {}
    return jsonify({"success": True, "row_count": kms.row_count(), "checkpoint": ck})


if __name__ == "__main__":
    port = int(os.getenv("CUSTOMER_ORDER_PORT", "3003"))
    app.run(host="0.0.0.0", port=port, debug=False)
