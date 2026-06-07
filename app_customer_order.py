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

from flask import Flask, jsonify, make_response, request, send_from_directory, session
from flask_cors import CORS

from settings import FLASK_SECRET_KEY
import production_helpers as ph

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
def api_health():
    return jsonify({"ok": True, "service": "customer_order", "port": 3003})


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
    if request.endpoint == "api_health":
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


def _no_cache_html(resp):
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/")
def index():
    return _no_cache_html(make_response(send_from_directory(".", "index_customer_order.html")))


@app.route("/guanli")
@app.route("/guanli/")
def guanli_index():
    return _no_cache_html(make_response(send_from_directory(".", "index_customer_order.html")))


@app.route("/guanli/login/submit", methods=["POST"])
def guanli_login_submit_direct():
    import guanli_server_login as _gsl
    return _gsl.handle_guanli_form_login()


@app.route("/guanli/login")
@app.route("/login_guanli.html")
def guanli_login_page():
    return _no_cache_html(make_response(send_from_directory(".", "login_guanli.html")))


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


from mp_api import mp_bp

app.register_blueprint(mp_bp)


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


@app.route("/api/perm/route_data")
def api_co_perm_route_data():
    err = require_admin()
    if err:
        return err
    bundle = emp_store.load_permission_bundle()
    return jsonify({
        "success": True,
        "employee_step_whitelist": bundle.get("employee_step_whitelist") or {},
        "order_routes": bundle.get("order_routes") or [],
    })


@app.route("/api/platform_products")
def api_platform_products():
    """按店铺/商品ID/规格名/规格ID搜索平台商品"""
    err = require_admin()
    if err:
        return err
    shop = request.args.get("shop", "").strip()
    pid = request.args.get("product_id", "").strip()
    spec_name = request.args.get("spec_name", "").strip()
    spec_id = request.args.get("spec_id", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(10, int(request.args.get("per_page", 20))))

    import pymysql

    cfg = {
        "host": os.getenv("MYSQL_HOST", "rm-7xv9u0s6tr3e24tg6.mysql.rds.aliyuncs.com"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "sanyang_app"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": "sanyang",
        "charset": "utf8mb4",
    }
    conn = pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)
    try:
        cur = conn.cursor()
        where = []
        params = []
        if shop:
            where.append("shop_name LIKE %s")
            params.append(f"%{shop}%")
        if pid:
            where.append("platform_product_id = %s")
            params.append(pid)
        if spec_name:
            where.append("platform_spec_name LIKE %s")
            params.append(f"%{spec_name}%")
        if spec_id:
            where.append("platform_spec_id = %s")
            params.append(spec_id)

        base_where = " AND ".join(where) if where else "1=1"

        cur.execute(f"SELECT COUNT(*) AS total FROM platform_products WHERE {base_where}", params)
        total = cur.fetchone()["total"]

        offset = (page - 1) * per_page
        cur.execute(
            f"SELECT id, shop_name, platform_product_id, platform_spec_name, platform_spec_id, created_at "
            f"FROM platform_products WHERE {base_where} ORDER BY id DESC LIMIT %s OFFSET %s",
            params + [per_page, offset]
        )
        rows = cur.fetchall()
        cur.close()
        return jsonify({
            "success": True,
            "data": rows,
            "total": total,
            "page": page,
            "per_page": per_page,
        })
    finally:
        conn.close()


@app.route("/api/perm/route_save", methods=["POST"])
def api_co_perm_route_save():
    err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        result = emp_store.save_permission_bundle({
            "employee_step_whitelist": data.get("employee_step_whitelist", {}),
            "order_routes": data.get("order_routes", []),
        })
        return jsonify({"success": True, **result})
    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# 功能1: 报表分析API
# ---------------------------------------------------------------------------

@app.route("/api/report/summary")
def api_report_summary():
    """今日订单/报工/完成/待产/本月概览"""
    from datetime import date, datetime
    import pymysql
    from settings import DB_CONFIG

    today = date.today()
    today_str = today.isoformat()

    # 加载订单缓存 (MySQL order_cache_store)
    orders = ph.load_cache_orders()

    # 今日订单
    today_orders = [o for o in orders if ph.order_on_date(o, today_str)]
    today_order_count = len(today_orders)
    month_orders = [
        o for o in orders
        if ph.order_on_date(o, today_str[:7] + "-01")
    ]  # approximate, we'll do proper month filter
    # Proper month filter
    month_orders = []
    for o in orders:
        dk = ph.order_date_key(o)
        if dk and dk[:7] == today_str[:7]:
            month_orders.append(o)
    month_order_count = len(month_orders)

    # 待生产订单: status != 'done'
    pending_orders = [o for o in orders if str(o.get("order_status") or o.get("status") or "") != "done"]
    # also check so_status / refund_status etc.
    pending_count = 0
    for o in orders:
        st = str(o.get("order_status") or o.get("status") or o.get("so_status") or "").strip().lower()
        if st != "done":
            pending_count += 1

    # MySQL scan_logs 今日数据
    scan_today = []
    try:
        db = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute(
            "SELECT order_id, step_name, worker, created_at FROM scan_logs WHERE DATE(created_at)=%s",
            (today_str,),
        )
        scan_today = cur.fetchall()
        cur.close()
        db.close()
    except Exception as e:
        print(f"[report/summary] scan_logs 查询失败: {e}")
        scan_today = []

    today_scan_count = len(scan_today)
    workers_today = set()
    for row in scan_today:
        w = (row.get("worker") or "").strip()
        if w:
            workers_today.add(w)

    # 今日完成订单：报工次数 >= 工序数（粗略）
    # 从 production_flows 或 scan_logs 分组计数
    order_scan_counts: dict[str, int] = {}
    for row in scan_today:
        oid = str(row.get("order_id") or "")
        if oid:
            order_scan_counts[oid] = order_scan_counts.get(oid, 0) + 1

    # 工序数: 从 production_flows 读，或按模板估算
    today_completed = 0
    try:
        db = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        for oid, sc in order_scan_counts.items():
            cur.execute("SELECT steps_json FROM production_flows WHERE order_id=%s", (oid,))
            row = cur.fetchone()
            if row:
                steps = ph.parse_flow_steps(row.get("steps_json"))
                total_steps = len(steps)
                if total_steps > 0 and sc >= total_steps:
                    today_completed += 1
        cur.close()
        db.close()
    except Exception as e:
        print(f"[report/summary] production_flows 查询失败: {e}")

    # 本月预估收入 - 从 orders_cache 订单总金额粗略汇总
    month_revenue_estimate = None
    try:
        total_amt = 0.0
        has_amt = False
        for o in month_orders:
            amt_v = o.get("payment") or o.get("total_amount") or o.get("pay_amount") or 0
            try:
                total_amt += float(amt_v)
                has_amt = True
            except (TypeError, ValueError):
                pass
        if has_amt:
            month_revenue_estimate = round(total_amt, 2)
    except Exception:
        month_revenue_estimate = None

    return jsonify({
        "today_orders": today_order_count,
        "today_scan_count": today_scan_count,
        "today_workers": len(workers_today),
        "today_completed_orders": today_completed,
        "pending_orders": pending_count,
        "month_orders": month_order_count,
        "month_revenue_estimate": month_revenue_estimate,
    })


@app.route("/api/report/trend")
def api_report_trend():
    """过去 N 天每日数据 [{date, orders_count, scan_count, workers_count}]"""
    from datetime import date, datetime, timedelta
    import pymysql
    from settings import DB_CONFIG

    days = max(1, min(365, int(request.args.get("days", "30"))))
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    # 加载订单
    orders = ph.load_cache_orders()

    # 按天查 scan_logs
    scan_rows = []
    try:
        db = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute(
            "SELECT DATE(created_at) AS d, COUNT(*) AS cnt, COUNT(DISTINCT worker) AS wc "
            "FROM scan_logs WHERE created_at >= %s GROUP BY DATE(created_at) ORDER BY d",
            (start_date.isoformat(),),
        )
        scan_rows = cur.fetchall()
        cur.close()
        db.close()
    except Exception as e:
        print(f"[report/trend] scan_logs 查询失败: {e}")

    scan_map = {}
    for r in scan_rows:
        d = r.get("d")
        if isinstance(d, date):
            d = d.isoformat()
        else:
            d = str(d or "")[:10]
        scan_map[d] = {
            "scan_count": int(r.get("cnt", 0)),
            "workers_count": int(r.get("wc", 0)),
        }

    result = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).isoformat()
        orders_count = sum(1 for o in orders if ph.order_on_date(o, d))
        s = scan_map.get(d, {})
        result.append({
            "date": d,
            "orders_count": orders_count,
            "scan_count": s.get("scan_count", 0),
            "workers_count": s.get("workers_count", 0),
        })

    return jsonify(result)


@app.route("/api/report/employee")
def api_report_employee():
    """指定日期每位员工的报工统计"""
    from datetime import date, datetime, timedelta
    import pymysql
    from settings import DB_CONFIG

    date_str = (request.args.get("date") or "").strip()
    if not date_str:
        date_str = date.today().isoformat()

    rows = []
    try:
        db = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        cur = db.cursor()
        cur.execute(
            "SELECT order_id, step_name, worker, created_at FROM scan_logs "
            "WHERE DATE(created_at)=%s ORDER BY id ASC",
            (date_str,),
        )
        rows = cur.fetchall()
        cur.close()
        db.close()
    except Exception as e:
        print(f"[report/employee] 查询失败: {e}")
        return jsonify([])

    # 按 worker 分组
    from collections import OrderedDict
    worker_map: dict[str, dict] = OrderedDict()
    for r in rows:
        w = (r.get("worker") or "").strip()
        if not w:
            continue
        if w not in worker_map:
            worker_map[w] = {
                "name": w,
                "scan_count": 0,
                "steps": [],
                "first_scan": None,
                "last_scan": None,
            }
        data = worker_map[w]
        data["scan_count"] += 1
        sn = r.get("step_name") or ""
        if sn and sn not in data["steps"]:
            data["steps"].append(sn)
        t = r.get("created_at")
        if isinstance(t, datetime):
            ts = t.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts = str(t or "")
        if data["first_scan"] is None or ts < data["first_scan"]:
            data["first_scan"] = ts
        if data["last_scan"] is None or ts > data["last_scan"]:
            data["last_scan"] = ts

    return jsonify(list(worker_map.values()))


@app.route("/api/report/product")
def api_report_product():
    """指定时间段按产品类型统计"""
    from datetime import date, datetime, timedelta
    import production_spec as _ps

    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    if not date_from:
        date_from = (date.today() - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = date.today().isoformat()

    orders = ph.load_cache_orders()
    type_map: dict[str, dict] = {}
    for o in orders:
        dk = ph.order_date_key(o)
        if not dk:
            continue
        if dk < date_from or dk > date_to:
            continue
        # 用订单级 infer_order_type 判断产品类型
        order_type = ph.infer_order_type(o)
        if order_type not in type_map:
            type_map[order_type] = {"product_type": order_type, "order_count": 0, "total_qty": 0}
        type_map[order_type]["order_count"] += 1
        for item in o.get("items") or []:
            if not isinstance(item, dict):
                continue
            try:
                type_map[order_type]["total_qty"] += int(item.get("qty") or 0)
            except (TypeError, ValueError):
                pass

    return jsonify(sorted(type_map.values(), key=lambda x: -x["total_qty"]))


# ---------------------------------------------------------------------------
# 功能2: 生产工单API
# ---------------------------------------------------------------------------

@app.route("/api/workorder/order/<order_id>")
def api_workorder_order(order_id):
    """生成订单的生产工单数据"""
    import production_spec as _ps
    from settings import DB_CONFIG

    orders = ph.load_cache_orders()
    o = ph.find_order_in_cache(orders, order_id)
    if not o:
        return jsonify({"success": False, "error": f"未找到订单 {order_id}"}), 404

    oid = ph.internal_order_id(o)
    so_id = str(o.get("so_id") or o.get("tid") or oid or "")
    customer = str(o.get("receiver_name") or o.get("buyer_nick") or "")
    shop_name = str(o.get("shop_name") or "")
    created_at = str(o.get("pay_time") or o.get("created") or "")

    # 获取工序
    try:
        bundle = emp_store.load_permission_bundle()
        process_tree = bundle.get("processes", [])
    except Exception:
        process_tree = []
    order_type = ph.infer_order_type(o)
    flow = ph.get_or_create_flow_steps(DB_CONFIG, process_tree, oid, order_type)
    steps = [s["step"] for s in flow]

    # 解析 items
    items_out = []
    for item in (o.get("items") or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("spec") or "")
        spec = str(item.get("spec") or item.get("display") or "")
        qty = int(item.get("qty") or 0)
        attrs = ph.item_buyer_attrs(item)
        product_type = ph.infer_order_type(o)
        material = config_json.match_material_from_mapping(attrs, None) if hasattr(config_json, "match_material_from_mapping") else ""
        dimensions = _ps.parse_dimensions_for_item(attrs)
        # 计算纸板尺寸
        calc_result = {}
        if dimensions.get("l") and dimensions.get("w") and dimensions.get("h"):
            try:
                l = dimensions["l"]
                w = dimensions["w"]
                h = dimensions["h"]
                if product_type in ("飞机盒", "飞机盒内盒"):
                    paper_l = (w + h) * 2 + 4
                    paper_w = l + h + 2
                    paper_g = round((paper_l * paper_w) / 10000 * 0.25, 2)
                    paper_cost = round(paper_g * 2.8, 2)
                elif product_type == "纸箱":
                    paper_l = (w + h) * 2 + 6
                    paper_w = l + h + 4
                    paper_g = round((paper_l * paper_w) / 10000 * 0.35, 2)
                    paper_cost = round(paper_g * 3.2, 2)
                else:
                    paper_l = (w + h) * 2 + 4
                    paper_w = l + h + 2
                    paper_g = round((paper_l * paper_w) / 10000 * 0.25, 2)
                    paper_cost = round(paper_g * 2.8, 2)
                calc_result = {
                    "paper_l": round(paper_l, 1),
                    "paper_w": round(paper_w, 1),
                    "paper_g": paper_g,
                    "paper_cost": paper_cost,
                }
            except Exception:
                pass
        items_out.append({
            "name": name,
            "spec": spec,
            "qty": qty,
            "product_type": product_type,
            "material": material,
            "dimensions": {"l": dimensions.get("l"), "w": dimensions.get("w"), "h": dimensions.get("h")},
            "calc_result": calc_result,
        })

    return jsonify({
        "order_id": oid,
        "so_id": so_id,
        "customer": customer,
        "shop_name": shop_name,
        "items": items_out,
        "steps": steps,
        "created_at": created_at,
    })


@app.route("/api/workorder/print", methods=["POST"])
def api_workorder_print():
    """生成打印工单的HTML"""
    data = request.get_json(silent=True) or {}
    order_ids = data.get("order_ids", [])
    if not isinstance(order_ids, list) or not order_ids:
        return jsonify({"success": False, "error": "order_ids 必填"}), 400

    orders = ph.load_cache_orders()
    lines = []
    for oid in order_ids:
        o = ph.find_order_in_cache(orders, str(oid).strip())
        if not o:
            continue
        oid_str = ph.internal_order_id(o)
        shop = str(o.get("shop_name") or "")
        items_html = ""
        for item in (o.get("items") or []):
            if not isinstance(item, dict):
                continue
            spec = str(item.get("spec") or item.get("name") or "")
            qty = int(item.get("qty") or 0)
            items_html += f"<tr><td>{spec}</td><td>{qty}</td></tr>"
        lines.append(f"""
        <div class="workorder-page">
            <h3>工单 #{oid_str}</h3>
            <p>店铺: {shop}</p>
            <table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
                <thead><tr><th>品名/规格</th><th>数量</th></tr></thead>
                <tbody>{items_html}</tbody>
            </table>
            <hr/>
        </div>""")

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
        body {{ font-family: SimSun, serif; font-size: 14px; }}
        .workorder-page {{ page-break-after: always; padding: 20px; }}
        table {{ margin-top: 10px; }}
        h3 {{ margin: 0 0 5px 0; }}
    </style>
</head><body>
    {''.join(lines)}
    <script>window.print();</script>
</body></html>"""

    return jsonify({"html": html})


@app.route("/api/workorder/scan/<order_id>")
def api_workorder_scan(order_id):
    """扫码后生产工单简化版"""
    import production_spec as _ps
    from settings import DB_CONFIG

    orders = ph.load_cache_orders()
    o = ph.find_order_in_cache(orders, order_id)
    if not o:
        return jsonify({"success": False, "error": f"未找到订单 {order_id}"}), 404

    oid = ph.internal_order_id(o)
    try:
        bundle = emp_store.load_permission_bundle()
        process_tree = bundle.get("processes", [])
        order_routes = bundle.get("order_routes")
    except Exception:
        process_tree = []
        order_routes = None
    order_type = ph.infer_order_type(o)
    flow = ph.get_or_create_flow_steps(DB_CONFIG, process_tree, oid, order_type,
                                       order=o, order_routes=order_routes)

    # 当前工序（第一个未完成的）
    current_step = ""
    reportable_steps = []
    for s in flow:
        if not s.get("done"):
            if not current_step:
                current_step = s["step"]
            reportable_steps.append(s["step"])

    # 简约版 items
    items_simple = []
    for item in (o.get("items") or []):
        if not isinstance(item, dict):
            continue
        spec = str(item.get("spec") or item.get("name") or "")
        qty = int(item.get("qty") or 0)
        attrs = ph.item_buyer_attrs(item)
        pt = ph.infer_order_type(o)
        dims = _ps.parse_dimensions_for_item(attrs)
        items_simple.append({
            "name": spec,
            "spec": spec,
            "qty": qty,
            "product_type": pt,
            "dimensions": {"l": dims.get("l"), "w": dims.get("w"), "h": dims.get("h")},
        })

    return jsonify({
        "order_id": oid,
        "shop_name": str(o.get("shop_name") or ""),
        "customer": str(o.get("receiver_name") or o.get("buyer_nick") or ""),
        "items": items_simple,
        "current_step": current_step,
        "reportable_steps": reportable_steps,
    })


if __name__ == "__main__":
    port = int(os.getenv("CUSTOMER_ORDER_PORT", "3003"))
    app.run(host="0.0.0.0", port=port, debug=False)
