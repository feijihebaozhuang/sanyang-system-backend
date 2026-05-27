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
def _session_cookie_secure() -> bool:
    v = (os.getenv("SESSION_COOKIE_SECURE") or "").strip().lower()
    if v in ("0", "false", "no"):
        return False
    if v in ("1", "true", "yes"):
        return True
    return False


app.config["SESSION_COOKIE_SECURE"] = _session_cookie_secure()

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
def _adjust_session_cookie():
    """反代后按实际协议设置 Secure，避免 HTTPS 站点 Cookie 写不进去。"""
    proto = (request.headers.get("X-Forwarded-Proto") or request.scheme or "").lower()
    if proto == "https":
        app.config["SESSION_COOKIE_SECURE"] = True
    elif proto == "http":
        app.config["SESSION_COOKIE_SECURE"] = False


@app.before_request
def _ensure_co_tables():
    if request.endpoint == "health":
        return None
    try:
        _bootstrap_tables()
    except Exception as e:
        print(f"[3003] 表初始化失败: {e}")
        if request.endpoint not in ("login", "index", "static_files"):
            raise


def _auth_token_for(username: str) -> str:
    return hashlib.sha256(f"{FLASK_SECRET_KEY}:{username}".encode()).hexdigest()[:32]


def resolve_login_user() -> dict | None:
    if co_store is None:
        return None
    hdr_user = (request.headers.get("X-Sanyang-User") or "").strip()
    hdr_tok = (request.headers.get("X-Sanyang-Token") or "").strip()
    if hdr_user and hdr_tok and hdr_tok == _auth_token_for(hdr_user):
        user = co_store.get_admin_by_username(hdr_user)
        if user and co_store.is_account_enabled(user.get("enabled")):
            return user
    username = session.get("username")
    if username:
        user = co_store.get_admin_by_username(username)
        if user and co_store.is_account_enabled(user.get("enabled")):
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


from mp_api import mp_bp

app.register_blueprint(mp_bp)


@app.route("/api/health")
def api_health():
    return jsonify({"ok": True, "service": "customer_order", "port": 3003})


@app.route("/api/login", methods=["POST"])
def login():
    try:
        _bootstrap_tables()
    except Exception as e:
        print(f"[3003 login] bootstrap: {e}")
        return jsonify({"success": False, "message": "服务初始化失败，请联系管理员"}), 503
    if co_store is None:
        return jsonify({"success": False, "message": "服务未就绪"}), 503

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return jsonify({"success": False, "message": "请输入账号和密码"})
    try:
        user = co_store.authenticate_admin_user(username, password)
    except Exception as e:
        print(f"[3003 login] {e}")
        import traceback

        traceback.print_exc()
        return jsonify(
            {
                "success": False,
                "message": "数据库连接失败，请检查 MySQL 配置或服务是否启动",
            }
        ), 503
    if not user:
        return jsonify({"success": False, "message": "账号或密码错误"})
    session.permanent = True
    session["username"] = user.get("username") or username
    session.modified = True
    payload = _user_payload(user)
    resp = jsonify({"success": True, "user": payload})
    return resp


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
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    limit = min(int(request.args.get("limit") or 100), 500)
    offset = max(int(request.args.get("offset") or 0), 0)
    cs_inc = (request.args.get("cs_include_unassigned") or "").lower() in ("1", "true", "yes")
    cs_sid = None
    if cs_staff_id is not None and str(cs_staff_id).strip() != "":
        cs_sid = int(cs_staff_id)
    items, total = co_store.list_orders(
        status=status,
        customer_id=int(customer_id) if customer_id else None,
        cs_staff_id=cs_sid,
        cs_include_unassigned=cs_inc,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
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
        item = emp_store.add_employee_full(
            data.get("name") or "",
            position=data.get("position") or "",
            group=data.get("group") or "其他",
            dept=data.get("dept") or "美丽湾工厂部",
        )
        return jsonify({"success": True, "item": item})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 500


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


@app.route("/api/perm/users/accounts")
def api_perm_users_accounts():
    err = require_admin()
    if err:
        return err
    return jsonify({"success": True, "items": emp_store.list_login_accounts()})


@app.route("/api/perm/users/sync", methods=["POST"])
def api_perm_users_sync():
    err = require_admin()
    if err:
        return err
    detail = emp_store.sync_login_accounts_from_employees()
    return jsonify({"success": True, "message": f"已同步显示名 {detail.get('fixed_display_names', 0)} 条", "detail": detail})


@app.route("/api/perm/users/save", methods=["POST"])
def api_perm_users_save():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        emp_name = (data.get("employee_name") or "").strip()
        disp = (data.get("display_name") or "").strip()
        if emp_name and not disp:
            disp = emp_name
        item = emp_store.upsert_user(
            data.get("username") or "",
            old_username=(data.get("old_username") or "").strip(),
            password=(data.get("password") or "").strip(),
            display_name=disp,
            role=(data.get("role") or "员工").strip(),
            employee_name=emp_name,
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


@app.route("/api/admin/km_sku/search")
def api_km_sku_search():
    err = require_admin()
    if err:
        return err
    import km_sku_map_store as kms

    limit = min(int(request.args.get("limit") or 50), 200)
    offset = max(int(request.args.get("offset") or 0), 0)
    items, total = kms.search_rows(
        keyword=(request.args.get("keyword") or "").strip(),
        outer_id=(request.args.get("outer_id") or "").strip(),
        product_type=(request.args.get("product_type") or "").strip(),
        limit=limit,
        offset=offset,
    )
    return jsonify({"success": True, "items": items, "total": total})


@app.route("/api/admin/km_sku/save", methods=["POST"])
def api_km_sku_save():
    err = require_admin()
    if err:
        return err
    import km_sku_map_store as kms

    data = request.get_json(silent=True) or {}
    try:
        item = kms.upsert_one(data)
        return jsonify({"success": True, "item": item})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------- 员工主数据 / 回收站 / 报价 / 店铺（对齐 3001 权限页） ----------
import admin_shared_store as admin_store
import config_json


@app.route("/api/employees")
def api_employees_list():
    err = require_admin()
    if err:
        return err
    return jsonify(emp_store.list_employees_full())


@app.route("/api/employee/add", methods=["POST"])
def api_employee_add():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        item = emp_store.add_employee_full(
            data.get("name") or "",
            position=data.get("position") or "",
            group=data.get("group") or "",
            phone=data.get("phone") or "",
            dept=data.get("dept") or "美丽湾工厂部",
        )
        return jsonify({"success": True, "message": "添加成功", "item": item})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/employee/update", methods=["POST"])
def api_employee_update():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        emp_store.update_employee_full(
            data.get("old_name") or data.get("name") or "",
            name=data.get("name") or "",
            position=data.get("position") or "",
            group=data.get("group") or "",
            phone=data.get("phone") or "",
            dept=data.get("dept") or "",
        )
        return jsonify({"success": True, "message": "更新成功"})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/employee/delete", methods=["POST"])
def api_employee_delete():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "name 必填"}), 400
    try:
        emp_store.resign_employee(name, operator=session.get("username", "admin"))
        return jsonify({"success": True, "message": "已标记为离职"})
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400


@app.route("/api/employee/resigned")
def api_employee_resigned():
    err = require_admin()
    if err:
        return err
    return jsonify({"employees": emp_store.load_resigned_employees()})


@app.route("/api/employee/restore", methods=["POST"])
def api_employee_restore():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "name 必填"}), 400
    emp_store.restore_resigned_employee(name)
    return jsonify({"success": True, "message": "已恢复"})


@app.route("/api/employee/delete_resigned", methods=["POST"])
def api_employee_delete_resigned():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "name 必填"}), 400
    emp_store.delete_resigned_record(name)
    return jsonify({"success": True, "message": "已删除"})


@app.route("/api/quote_data")
def api_quote_data():
    err = require_admin()
    if err:
        return err
    qd = admin_store.load_quote_data()
    if not qd:
        return jsonify({"success": False, "error": "报价数据未加载"})
    return jsonify({"success": True, "data": qd})


@app.route("/api/quote/save_config", methods=["POST"])
def api_quote_save_config():
    err = require_admin()
    if err:
        return err
    patch = request.get_json(silent=True) or {}
    from quote_config_merge import merge_quote_config

    existing = admin_store.load_quote_data() or {}
    merged = merge_quote_config(existing, patch)
    if not admin_store.save_quote_data(merged):
        return jsonify({"success": False, "error": "保存失败（MySQL/quote_data.json 均不可写）"}), 500
    sync_detail: dict = {}
    if isinstance(patch, dict) and "material_mapping" in patch:
        bundle = emp_store.load_permission_bundle()
        sync_detail = config_json.sync_production_mapping_from_quote(
            bundle, merged.get("material_mapping")
        )
    msg = "报价配置已保存"
    if sync_detail.get("vault_error"):
        msg += f"（vault 警告: {sync_detail['vault_error']}）"
    return jsonify({"success": True, "message": msg, "detail": sync_detail})


@app.route("/api/perm/material_mapping")
def api_perm_material_mapping_get():
    err = require_admin()
    if err:
        return err
    rows = admin_store.load_material_mapping_admin()
    return jsonify({"success": True, "material_mapping": rows})


@app.route("/api/perm/material_mapping/save", methods=["POST"])
def api_perm_material_mapping_save():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    rows = data.get("material_mapping")
    if not isinstance(rows, list):
        return jsonify({"success": False, "error": "material_mapping 须为数组"}), 400
    quote_ok, quote_err, saved_rows = admin_store.save_quote_mapping(rows)
    prod_map = config_json.quote_rows_to_production_mapping(saved_rows)
    try:
        perm_result = emp_store.save_permission_bundle(
            {"production_material_mapping": prod_map}
        )
        sync_detail = perm_result.get("detail") or {}
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 500
    if not quote_ok:
        return jsonify(
            {
                "success": False,
                "error": quote_err or "quote_config / quote_data.json 写入失败",
                "detail": sync_detail,
            }
        ), 500
    msg = f"材料映射已保存（{len(prod_map)} 条）"
    if sync_detail.get("vault_error"):
        msg += f"（vault: {sync_detail['vault_error']}）"
    return jsonify(
        {
            "success": True,
            "message": msg,
            "mapping_count": len(prod_map),
            "quote_ok": quote_ok,
            "material_mapping": saved_rows,
            "detail": sync_detail,
        }
    )


@app.route("/api/shop-config", methods=["GET"])
def api_shop_config_get():
    err = require_admin()
    if err:
        return err
    config = admin_store.load_shop_config()
    return jsonify({"success": True, "config": config, "shop_config": config})


@app.route("/api/shop-config", methods=["POST"])
def api_shop_config_add():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        item = admin_store.add_shop_item(data)
        return jsonify({"success": True, "message": "已添加", "item": item})
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/shop-config/<config_id>", methods=["PUT"])
def api_shop_config_update(config_id):
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    item = admin_store.update_shop_item(config_id, data)
    if not item:
        return jsonify({"success": False, "error": "未找到"}), 404
    return jsonify({"success": True, "message": "已更新", "item": item})


@app.route("/api/shop-config/<config_id>", methods=["DELETE"])
def api_shop_config_delete(config_id):
    err = require_admin()
    if err:
        return err
    admin_store.delete_shop_item(config_id)
    return jsonify({"success": True, "message": "已删除"})


if __name__ == "__main__":
    port = int(os.getenv("CUSTOMER_ORDER_PORT", "3003"))
    app.run(host="0.0.0.0", port=port, debug=False)
