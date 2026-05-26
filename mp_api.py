# -*- coding: utf-8 -*-
"""小程序 API 路由（挂载到 app_customer_order）。"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, request

import customer_order_store as co_store
import mp_auth

mp_bp = Blueprint("mp", __name__, url_prefix="/api/mp")

_QUOTE_PROXY = os.getenv("MP_QUOTE_PROXY_BASE", "http://127.0.0.1:3001").rstrip("/")


def _proxy_json(method: str, path: str, payload: dict | None = None) -> dict:
    url = _QUOTE_PROXY + path
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"success": False, "error": raw[:300]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _customer_from_request():
    body = request.get_json(silent=True) or {}
    token = (request.headers.get("Authorization") or "").replace("Bearer ", "").strip()
    if not token:
        token = (body.get("token") or request.headers.get("X-Mp-Token") or "").strip()
    openid = (
        (body.get("openid") or request.headers.get("X-Mp-Openid") or "").strip()
    )
    cid = int(body.get("customer_id") or request.headers.get("X-Mp-Customer-Id") or 0)
    if openid and cid and token and mp_auth.verify_customer_token(openid, cid, token):
        cust = co_store.get_customer_by_id(cid)
        if cust and (cust.get("wx_openid") or "") == openid:
            return cust
    return None


def _cs_session_allowed(cs: dict) -> bool:
    if cs.get("auth_mode") == "pwd":
        user = mp_auth.find_user_by_username(cs.get("username") or "")
    else:
        staff = co_store.get_cs_staff(int(cs.get("cs_staff_id") or 0))
        en = (staff.get("employee_name") if staff else "") or cs.get("username") or ""
        user = mp_auth.find_user_by_employee_name(en)
    return mp_auth.user_can_use_quote_weapp(user)


def _cs_from_request():
    body = request.get_json(silent=True) or {}
    token = (request.headers.get("Authorization") or "").replace("Bearer ", "").strip()
    if not token:
        token = (body.get("token") or request.headers.get("X-Mp-Token") or "").strip()
    openid = (body.get("openid") or request.headers.get("X-Mp-Openid") or "").strip()
    cs_id_raw = body.get("cs_staff_id") or request.headers.get("X-Mp-Cs-Id") or ""
    cs_id = int(cs_id_raw) if cs_id_raw not in ("", None) else None
    cs = None
    if openid and cs_id and token and mp_auth.verify_cs_wx_token(openid, int(cs_id), token):
        staff = co_store.find_cs_staff_by_openid(openid)
        if staff and int(staff.get("id") or 0) == int(cs_id):
            cs = {
                "username": staff.get("employee_name") or "",
                "cs_staff_id": cs_id,
                "openid": openid,
                "auth_mode": "wx",
            }
    if not cs:
        username = (body.get("username") or request.headers.get("X-Mp-User") or "").strip()
        if username and token and mp_auth.verify_cs_token(username, cs_id, token):
            cs = {"username": username, "cs_staff_id": cs_id, "auth_mode": "pwd"}
    if cs and _cs_session_allowed(cs):
        return cs
    return None


def _require_cs_or_forbidden():
    body = request.get_json(silent=True) or {}
    token = (request.headers.get("Authorization") or "").replace("Bearer ", "").strip()
    if not token:
        token = (body.get("token") or request.headers.get("X-Mp-Token") or "").strip()
    if not token:
        return None, (jsonify({"success": False, "error": "请先登录", "code": 401}), 401)
    cs = _cs_from_request()
    if cs:
        return cs, None
    # 有 token 但角色不对
    openid = (request.headers.get("X-Mp-Openid") or "").strip()
    username = (request.headers.get("X-Mp-User") or "").strip()
    if openid or username:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "仅客服和超级管理员可使用报价小程序",
                    "code": 403,
                }
            ),
            403,
        )
    return None, (jsonify({"success": False, "error": "请先登录", "code": 401}), 401)


@mp_bp.route("/wx/login", methods=["POST"])
def mp_wx_login():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    try:
        sess = mp_auth.wx_code_to_session(code, app="customer")
        openid = sess["openid"]
        cust = co_store.ensure_customer_for_openid(
            openid,
            name=(data.get("name") or "").strip(),
            phone=(data.get("phone") or "").strip(),
        )
        cid = int(cust["id"])
        tok = mp_auth.customer_token(openid, cid)
        return jsonify(
            {
                "success": True,
                "openid": openid,
                "customer_id": cid,
                "token": tok,
                "customer": cust,
                "dev_mode": sess.get("dev_mode", False),
            }
        )
    except (ValueError, RuntimeError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


@mp_bp.route("/categories")
def mp_categories():
    items = co_store.list_categories(include_disabled=False)
    return jsonify({"success": True, "items": items})


@mp_bp.route("/quote_data")
def mp_quote_data():
    _, err = _require_cs_or_forbidden()
    if err:
        return err
    res = _proxy_json("GET", "/api/quote_data")
    return jsonify(res)


@mp_bp.route("/quote/calculate", methods=["POST"])
def mp_quote_calculate():
    _, err = _require_cs_or_forbidden()
    if err:
        return err
    payload = request.get_json(silent=True) or {}
    cat = (payload.get("product_category_code") or payload.get("type") or "").strip()
    # 映射 co 分类码 → 报价 type
    type_map = {
        "zhengsquare": "zhengsquare-outer",
        "daikou": "daikou",
        "koudi": "koudi",
        "shuangcha": "shuangcha",
        "juxing": "qita",
        "zhenzhenmian": "pe",
    }
    if cat in type_map:
        payload = dict(payload)
        payload["type"] = type_map.get(cat, payload.get("type", "zhengsquare-outer"))
    res = _proxy_json("POST", "/api/quote/calculate", payload)
    return jsonify(res)


@mp_bp.route("/match", methods=["POST"])
def mp_match():
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


@mp_bp.route("/order/create", methods=["POST"])
def mp_order_create():
    cust = _customer_from_request()
    if not cust:
        return jsonify({"success": False, "error": "请先登录", "code": 401}), 401
    data = request.get_json(silent=True) or {}
    data["customer_id"] = cust["id"]
    phone = (data.get("phone") or data.get("customer_phone") or "").strip()
    if phone:
        co_store.upsert_customer(
            {
                "id": cust["id"],
                "name": cust.get("name") or "",
                "contact_name": cust.get("contact_name") or "",
                "phone": phone,
                "company": cust.get("company") or "",
                "assigned_cs_id": cust.get("assigned_cs_id"),
                "status": cust.get("status") or "active",
                "remark": cust.get("remark") or "",
            }
        )
    if not data.get("cs_staff_id") and cust.get("assigned_cs_id"):
        data["cs_staff_id"] = cust["assigned_cs_id"]
    data.setdefault("status", "pending_review")
    try:
        item = co_store.upsert_order(data, created_by=f"mp:{cust.get('id')}")
        return jsonify({"success": True, "item": item})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@mp_bp.route("/orders")
def mp_orders():
    cust = _customer_from_request()
    if not cust:
        return jsonify({"success": False, "error": "请先登录", "code": 401}), 401
    items, total = co_store.list_orders(customer_id=int(cust["id"]), limit=100)
    return jsonify({"success": True, "items": items, "total": total})


@mp_bp.route("/order/<int:order_id>")
def mp_order_detail(order_id: int):
    cust = _customer_from_request()
    if not cust:
        return jsonify({"success": False, "error": "请先登录", "code": 401}), 401
    item = co_store.get_order(order_id)
    if not item or int(item.get("customer_id") or 0) != int(cust["id"]):
        return jsonify({"success": False, "error": "订单不存在"}), 404
    return jsonify({"success": True, "item": item})


@mp_bp.route("/cs/login", methods=["POST"])
def mp_cs_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    code = (data.get("code") or "").strip()
    user, auth_err = mp_auth.verify_quote_weapp_password(username, password)
    if not user:
        return jsonify({"success": False, "error": auth_err or "登录失败"}), 401
    try:
        cs_staff_id = co_store.ensure_cs_staff_for_user(user)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    openid = ""
    if code:
        try:
            sess = mp_auth.wx_code_to_session(code, app="cs")
            openid = (sess.get("openid") or "").strip()
            if openid:
                co_store.bind_cs_staff_openid(int(cs_staff_id), openid)
        except (ValueError, RuntimeError) as e:
            return jsonify({"success": False, "error": str(e)}), 400
    en = (user.get("employee_name") or user.get("display_name") or "").strip()
    tok = mp_auth.cs_token(username, cs_staff_id)
    wx_tok = mp_auth.cs_wx_token(openid, int(cs_staff_id)) if openid else ""
    return jsonify(
        {
            "success": True,
            "username": username,
            "display_name": user.get("display_name") or username,
            "employee_name": en,
            "role": user.get("role") or "",
            "cs_staff_id": cs_staff_id,
            "token": tok,
            "openid": openid,
            "wx_token": wx_tok,
            "wx_bound": bool(openid),
        }
    )


@mp_bp.route("/cs/wx/login", methods=["POST"])
def mp_cs_wx_login():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return jsonify({"success": False, "error": "code 必填"}), 400
    try:
        sess = mp_auth.wx_code_to_session(code, app="cs")
        openid = (sess.get("openid") or "").strip()
        staff = co_store.find_cs_staff_by_openid(openid)
        if not staff:
            return jsonify(
                {
                    "success": False,
                    "need_bind": True,
                    "openid": openid,
                    "error": "首次使用请绑定 3001 账号",
                }
            ), 401
        user = mp_auth.find_user_by_employee_name(staff.get("employee_name") or "")
        if not mp_auth.user_can_use_quote_weapp(user):
            return jsonify(
                {
                    "success": False,
                    "error": "仅客服和超级管理员可使用报价小程序",
                    "code": 403,
                }
            ), 403
        cs_staff_id = int(staff["id"])
        tok = mp_auth.cs_wx_token(openid, cs_staff_id)
        return jsonify(
            {
                "success": True,
                "openid": openid,
                "cs_staff_id": cs_staff_id,
                "token": tok,
                "display_name": staff.get("employee_name") or "",
                "employee_name": staff.get("employee_name") or "",
                "role": (user or {}).get("role") or "",
                "phone": staff.get("phone") or "",
                "auth_mode": "wx",
            }
        )
    except (ValueError, RuntimeError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


@mp_bp.route("/cs/wx/bind", methods=["POST"])
def mp_cs_wx_bind():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not code:
        return jsonify({"success": False, "error": "code 必填"}), 400
    user, auth_err = mp_auth.verify_quote_weapp_password(username, password)
    if not user:
        return jsonify({"success": False, "error": auth_err or "绑定失败"}), 401
    try:
        sess = mp_auth.wx_code_to_session(code, app="cs")
        openid = (sess.get("openid") or "").strip()
        cs_staff_id = co_store.ensure_cs_staff_for_user(user)
        staff = co_store.bind_cs_staff_openid(int(cs_staff_id), openid)
        en = (user.get("employee_name") or user.get("display_name") or "").strip()
        tok = mp_auth.cs_wx_token(openid, int(cs_staff_id))
        return jsonify(
            {
                "success": True,
                "openid": openid,
                "cs_staff_id": cs_staff_id,
                "token": tok,
                "display_name": staff.get("employee_name") or en,
                "employee_name": staff.get("employee_name") or en,
                "role": user.get("role") or "",
                "phone": staff.get("phone") or "",
                "auth_mode": "wx",
            }
        )
    except (ValueError, RuntimeError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


@mp_bp.route("/cs/orders")
def mp_cs_orders():
    _, err = _require_cs_or_forbidden()
    if err:
        return err
    cs = _cs_from_request()
    status = (request.args.get("status") or "").strip()
    keyword = (request.args.get("keyword") or "").strip()
    cs_id = cs.get("cs_staff_id")
    if cs_id:
        items, total = co_store.list_orders(
            cs_staff_id=int(cs_id), status=status, keyword=keyword, limit=200
        )
    else:
        items, total = co_store.list_orders(status=status or "pending_review", keyword=keyword, limit=200)
    return jsonify({"success": True, "items": items, "total": total})


@mp_bp.route("/cs/order/<int:order_id>")
def mp_cs_order_detail(order_id: int):
    _, err = _require_cs_or_forbidden()
    if err:
        return err
    cs = _cs_from_request()
    item = co_store.get_order(order_id)
    if not item:
        return jsonify({"success": False, "error": "订单不存在"}), 404
    cs_id = cs.get("cs_staff_id")
    if cs_id and item.get("cs_staff_id") and int(item["cs_staff_id"]) != int(cs_id):
        return jsonify({"success": False, "error": "无权查看此订单"}), 403
    return jsonify({"success": True, "item": item})


@mp_bp.route("/cs/order/review", methods=["POST"])
def mp_cs_order_review():
    _, err = _require_cs_or_forbidden()
    if err:
        return err
    cs = _cs_from_request()
    data = request.get_json(silent=True) or {}
    oid = int(data.get("id") or data.get("order_id") or 0)
    if not oid:
        return jsonify({"success": False, "error": "order_id 必填"}), 400
    status = (data.get("status") or "").strip()
    if status not in ("approved", "rejected", "pending_review"):
        return jsonify({"success": False, "error": "无效 status"}), 400
    existing = co_store.get_order(oid)
    if not existing:
        return jsonify({"success": False, "error": "订单不存在"}), 404
    cs_id = cs.get("cs_staff_id")
    if cs_id and existing.get("cs_staff_id") and int(existing["cs_staff_id"]) != int(cs_id):
        return jsonify({"success": False, "error": "无权审核此订单"}), 403
    payload = dict(existing)
    payload["status"] = status
    payload["remark"] = (data.get("remark") or existing.get("remark") or "").strip()
    if cs_id:
        payload["cs_staff_id"] = cs_id
    item = co_store.upsert_order(payload, created_by=f"cs:{cs.get('username')}")
    return jsonify({"success": True, "item": item})
