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

# 内径 → 外径（与 3001 calculate_quote 一致，cm）
_INNER_TO_OUTER_DELTA = (1.5, 0.5, 0.5)

# 客户小程序算价响应中隐藏成本字段
_CUSTOMER_QUOTE_HIDE = frozenset(
    {
        "material_cost_per_unit",
        "total_cost",
        "unit_price",
        "suggested_multiplier",
        "suggested_price",
        "batch_multiplier",
        "batch_suggested_price",
        "paper_l_cm",
        "paper_w_cm",
        "paper_l_inch",
        "paper_w_inch",
        "gram_weight",
    }
)


def _inner_to_outer(l: float, w: float, h: float) -> tuple[float, float, float]:
    dl, dw, dh = _INNER_TO_OUTER_DELTA
    return l + dl, w + dw, h + dh


def _prepare_quote_payload(raw: dict) -> dict:
    """客户/小程序分类码 + 内外径 → 3001 报价 type 与尺寸。"""
    payload = dict(raw or {})
    cat = (payload.get("product_category_code") or payload.get("type") or "").strip()
    dim_kind = (payload.get("dim_kind") or "outer").strip() or "outer"
    is_inner = dim_kind == "inner"

    payload.setdefault("customer_type", "guangdong_retail")
    payload.setdefault("discount", 100)

    if cat in ("zhenzhenmian", "pe"):
        payload["type"] = "pe"
        return payload

    type_map = {
        "zhengsquare": "zhengsquare-outer",
        "daikou": "daikou",
        "koudi": "koudi",
        "shuangcha": "shuangcha",
        "juxing": "qita",
    }

    if cat == "zhengsquare":
        payload["type"] = "zhengsquare-inner" if is_inner else "zhengsquare-outer"
        if is_inner:
            l = float(payload.get("length") or 0)
            w = float(payload.get("width") or 0)
            h = float(payload.get("height") or 0)
            if l > 0 and w > 0 and h > 0:
                payload["_inner_dims"] = {"length": l, "width": w, "height": h}
    elif cat in type_map:
        payload["type"] = type_map[cat]
        if is_inner:
            l = float(payload.get("length") or 0)
            w = float(payload.get("width") or 0)
            h = float(payload.get("height") or 0)
            if l > 0 and w > 0 and h > 0:
                ol, ow, oh = _inner_to_outer(l, w, h)
                payload["length"] = ol
                payload["width"] = ow
                payload["height"] = oh
                payload["_inner_dims"] = {"length": l, "width": w, "height": h}
    elif cat.endswith("-inner") or cat.endswith("-outer"):
        payload["type"] = cat
    elif cat:
        payload["type"] = cat

    return payload


def _sanitize_customer_quote(res: dict) -> dict:
    if not res.get("success"):
        return res
    detail = res.get("detail")
    if not isinstance(detail, dict):
        return res
    out = dict(res)
    cleaned = {k: v for k, v in detail.items() if k not in _CUSTOMER_QUOTE_HIDE}
    cleaned["price_kind"] = "retail"
    out["detail"] = cleaned
    return out


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


def _cs_user_from_session(cs: dict) -> dict | None:
    if cs.get("auth_mode") == "pwd":
        return mp_auth.find_user_by_username(cs.get("username") or "")
    staff = co_store.get_cs_staff(int(cs.get("cs_staff_id") or 0))
    en = (staff.get("employee_name") if staff else "") or cs.get("username") or ""
    return mp_auth.find_user_by_employee_name(en)


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
    # 客户下单小程序需匿名读报价配置；与 3001/3002 /api/quote_data 一致，不做客服鉴权
    res = _proxy_json("GET", "/api/quote_data")
    return jsonify(res)


@mp_bp.route("/quote/calculate", methods=["POST"])
def mp_quote_calculate():
    # 客户下单算价；客服报价小程序共用此接口
    raw = request.get_json(silent=True) or {}
    for_customer = (raw.get("client") or "").strip() == "customer"
    payload = _prepare_quote_payload(raw)
    payload.pop("client", None)
    payload.pop("product_category_code", None)
    payload.pop("dim_kind", None)
    inner_dims = payload.pop("_inner_dims", None)
    res = _proxy_json("POST", "/api/quote/calculate", payload)
    if res.get("success") and isinstance(res.get("detail"), dict):
        detail = dict(res["detail"])
        if inner_dims:
            detail["inner_length"] = inner_dims.get("length")
            detail["inner_width"] = inner_dims.get("width")
            detail["inner_height"] = inner_dims.get("height")
            ol, ow, oh = _inner_to_outer(
                float(inner_dims.get("length") or 0),
                float(inner_dims.get("width") or 0),
                float(inner_dims.get("height") or 0),
            )
            detail["outer_length"] = round(ol, 2)
            detail["outer_width"] = round(ow, 2)
            detail["outer_height"] = round(oh, 2)
            detail["dimension_label"] = "内径转外径"
        res = dict(res)
        res["detail"] = detail
    if for_customer:
        res = _sanitize_customer_quote(res)
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


@mp_bp.route("/customer/profile", methods=["GET", "POST"])
def mp_customer_profile():
    cust = _customer_from_request()
    if not cust:
        return jsonify({"success": False, "error": "请先登录", "code": 401}), 401
    cid = int(cust["id"])
    if request.method == "GET":
        row = co_store.get_customer_by_id(cid)
        return jsonify({"success": True, "customer": row})
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    contact_name = (data.get("contact_name") or "").strip()
    address = (data.get("address") or "").strip()
    updated = co_store.upsert_customer(
        {
            "id": cid,
            "name": cust.get("name") or "",
            "contact_name": contact_name or cust.get("contact_name") or "",
            "phone": phone or cust.get("phone") or "",
            "address": address or cust.get("address") or "",
            "company": cust.get("company") or "",
            "assigned_cs_id": cust.get("assigned_cs_id"),
            "status": cust.get("status") or "active",
            "remark": cust.get("remark") or "",
        }
    )
    return jsonify({"success": True, "customer": updated})


@mp_bp.route("/order/create", methods=["POST"])
def mp_order_create():
    cust = _customer_from_request()
    if not cust:
        return jsonify({"success": False, "error": "请先登录", "code": 401}), 401
    data = request.get_json(silent=True) or {}
    data["customer_id"] = cust["id"]
    phone = (data.get("phone") or data.get("ship_phone") or data.get("customer_phone") or "").strip()
    contact_name = (data.get("contact_name") or data.get("ship_contact") or "").strip()
    address = (data.get("address") or data.get("ship_address") or "").strip()
    if phone or contact_name or address:
        co_store.upsert_customer(
            {
                "id": cust["id"],
                "name": cust.get("name") or "",
                "contact_name": contact_name or cust.get("contact_name") or "",
                "phone": phone or cust.get("phone") or "",
                "address": address or cust.get("address") or "",
                "company": cust.get("company") or "",
                "assigned_cs_id": cust.get("assigned_cs_id"),
                "status": cust.get("status") or "active",
                "remark": cust.get("remark") or "",
            }
        )
    data["ship_phone"] = phone
    data["ship_contact"] = contact_name
    data["ship_address"] = address
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
    status = (request.args.get("status") or "").strip() or "pending_review"
    keyword = (request.args.get("keyword") or "").strip()
    user = _cs_user_from_session(cs) if cs else None
    is_super = (user or {}).get("role") == "超级管理员"
    cs_id = cs.get("cs_staff_id") if cs else None
    if is_super:
        items, total = co_store.list_orders(status=status, keyword=keyword, limit=200)
    elif cs_id:
        items, total = co_store.list_orders(
            cs_staff_id=int(cs_id),
            cs_include_unassigned=(status == "pending_review"),
            status=status,
            keyword=keyword,
            limit=200,
        )
    else:
        items, total = co_store.list_orders(status=status, keyword=keyword, limit=200)
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


@mp_bp.route("/cs/order/ship", methods=["POST"])
def mp_cs_order_ship():
    """客服发货：填写快递公司/单号，订单变为已完成，客户小程序可查看。"""
    _, err = _require_cs_or_forbidden()
    if err:
        return err
    cs = _cs_from_request()
    data = request.get_json(silent=True) or {}
    oid = int(data.get("id") or data.get("order_id") or 0)
    if not oid:
        return jsonify({"success": False, "error": "order_id 必填"}), 400
    express_no = (data.get("express_no") or data.get("tracking_no") or "").strip()
    if not express_no:
        return jsonify({"success": False, "error": "请填写快递单号"}), 400
    express_company = (data.get("express_company") or data.get("logistics_company") or "快递").strip()
    existing = co_store.get_order(oid)
    if not existing:
        return jsonify({"success": False, "error": "订单不存在"}), 404
    cs_id = cs.get("cs_staff_id")
    if cs_id and existing.get("cs_staff_id") and int(existing["cs_staff_id"]) != int(cs_id):
        user = _cs_user_from_session(cs)
        if (user or {}).get("role") != "超级管理员":
            return jsonify({"success": False, "error": "无权操作此订单"}), 403
    if existing.get("status") not in ("approved", "in_production"):
        return jsonify({"success": False, "error": "仅「已通过/生产中」的订单可发货"}), 400
    payload = dict(existing)
    payload["express_company"] = express_company
    payload["express_no"] = express_no
    payload["status"] = "completed"
    if cs_id:
        payload["cs_staff_id"] = cs_id
    remark = (data.get("remark") or existing.get("remark") or "").strip()
    if remark:
        payload["remark"] = remark
    item = co_store.upsert_order(payload, created_by=f"cs:{cs.get('username')}")
    return jsonify({"success": True, "item": item})
