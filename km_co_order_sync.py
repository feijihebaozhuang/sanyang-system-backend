# -*- coding: utf-8 -*-
"""客户下单 co_order ↔ 快麦 ERP：审核后推单、发货后回写物流。"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any

import km_api

_KM_SHIPPED_STATUS = frozenset(
    {
        "SELLER_SEND_GOODS",
        "WAIT_BUYER_CONFIRM_GOODS",
        "FINISHED",
        "TRADE_FINISHED",
        "卖家已发货",
        "交易成功",
    }
)

_CATEGORY_TITLE = {
    "zhengsquare": "标准飞机盒",
    "daikou": "带扣飞机盒",
    "koudi": "扣底盒",
    "shuangcha": "双插盒",
    "juxing": "纸箱",
    "zhenzhenmian": "珍珠棉",
}


def km_co_shop_user_id() -> str:
    return (os.getenv("KM_CO_SHOP_USER_ID") or "").strip()


def km_co_enabled() -> bool:
    return bool(km_api.km_configured() and km_co_shop_user_id())


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_cn_address(full: str) -> dict[str, str]:
    """粗分解国内地址，供快麦 create.new 必填字段使用。"""
    raw = (full or "").strip()
    rest = raw
    state = city = district = ""

    m = re.match(r"^(.+?(?:省|自治区|特别行政区))", rest)
    if m:
        state = m.group(1)
        rest = rest[len(state) :]
    else:
        for p in ("北京市", "上海市", "天津市", "重庆市"):
            if rest.startswith(p):
                state = p
                rest = rest[len(p) :]
                break
            if rest.startswith(p[:2]):
                state = p
                rest = rest[len(p[:2]) :]
                break

    m = re.match(r"^(.+?(?:市|自治州|地区|盟))", rest)
    if m:
        city = m.group(1)
        rest = rest[len(city) :]

    m = re.match(r"^(.+?(?:区|县|市|旗))", rest)
    if m:
        district = m.group(1)
        rest = rest[len(district) :]

    detail = rest.strip() or raw or "待补充"
    if not state:
        state = "广东省"
    if not city:
        city = "东莞市"
    if not district:
        district = "市辖区"
    street = district if district != "市辖区" else "—"
    return {
        "receiverState": state,
        "receiverCity": city,
        "receiverDistrict": district,
        "receiverStreet": street,
        "receiverAddress": detail,
    }


def _trade_express(trade: dict) -> tuple[str, str]:
    company = (
        trade.get("logisticsCompany")
        or trade.get("expressCompany")
        or trade.get("expressName")
        or trade.get("companyName")
        or trade.get("cpName")
        or ""
    )
    if isinstance(company, dict):
        company = company.get("name") or company.get("companyName") or ""
    company = str(company).strip()

    no = (
        trade.get("outSid")
        or trade.get("expressNo")
        or trade.get("waybillCode")
        or trade.get("mailNo")
        or ""
    )
    no = str(no).strip()
    if not no:
        for line in trade.get("orders") or trade.get("orderList") or []:
            if not isinstance(line, dict):
                continue
            no = str(
                line.get("outSid")
                or line.get("expressNo")
                or line.get("invoiceNo")
                or ""
            ).strip()
            if no:
                break
    return company or "快递", no


def _trade_is_shipped(trade: dict) -> bool:
    st = km_api.km_resolve_sys_status(trade)
    if st in _KM_SHIPPED_STATUS:
        return True
    platform_st = str(trade.get("status") or trade.get("tradeStatus") or "").strip()
    if platform_st in ("WAIT_BUYER_CONFIRM_GOODS", "TRADE_FINISHED"):
        return True
    company, no = _trade_express(trade)
    return bool(no)


def _resolve_outer_id(order: dict, co_store) -> str:
    outer_id = (order.get("outer_id") or "").strip()
    if outer_id:
        return outer_id
    match = co_store.lookup_sku_match(
        (order.get("product_category_code") or "").strip(),
        float(order.get("length") or 0),
        float(order.get("width") or 0),
        float(order.get("height") or 0),
        (order.get("material") or "").strip(),
        (order.get("dim_kind") or "").strip(),
    )
    return (match or {}).get("outer_id") or ""


def build_km_trade_payload(order: dict, *, co_store) -> dict[str, Any]:
    shop_uid = km_co_shop_user_id()
    if not shop_uid:
        raise ValueError("未配置 KM_CO_SHOP_USER_ID（快麦客户下单专用店铺 userId）")

    tid = (order.get("km_tid") or order.get("order_no") or "").strip()
    if not tid:
        raise ValueError("订单缺少 order_no")

    outer_id = _resolve_outer_id(order, co_store)
    if not outer_id:
        raise ValueError("未匹配到快麦商家编码，请先在 km_sku_map 维护对应 SKU")

    phone = (order.get("ship_phone") or "").strip()
    if not re.fullmatch(r"1\d{10}", phone):
        raise ValueError("收货手机号格式有误，快麦推单需要 11 位手机号")

    contact = (order.get("ship_contact") or order.get("customer_contact") or "客户").strip()
    addr = parse_cn_address(order.get("ship_address") or "")

    qty = max(1, int(order.get("qty") or 1))
    unit_price = float(order.get("unit_price") or 0)
    total = float(order.get("total_price") or 0)
    if not total and unit_price:
        total = round(unit_price * qty, 2)
    if not total:
        total = unit_price or 0.01
    line_pay = f"{total:.2f}"
    line_price = f"{unit_price:.2f}" if unit_price else line_pay

    cat = (order.get("product_category_code") or "").strip()
    title = (
        order.get("category_name")
        or _CATEGORY_TITLE.get(cat)
        or "定制包装"
    )
    spec = f"{order.get('length')}×{order.get('width')}×{order.get('height')}"
    if order.get("material"):
        spec += f" {order['material']}"
    title = f"{title} {spec}".strip()

    now = _now_str()
    line = {
        "outerId": outer_id,
        "num": qty,
        "price": line_price,
        "payment": line_pay,
        "title": title[:120],
        "status": "WAIT_SELLER_SEND_GOODS",
    }

    payload: dict[str, Any] = {
        "tid": tid,
        "userId": shop_uid,
        "status": "WAIT_SELLER_SEND_GOODS",
        "receiverName": contact[:32],
        "receiverMobile": phone,
        "receiverPhone": phone,
        "payment": line_pay,
        "postFee": "0.00",
        "buyerNick": phone or contact,
        "buyerMessage": (order.get("remark") or "")[:200],
        "sellerMemo": f"客户下单 {order.get('order_no') or tid}"[:200],
        "created": now,
        "payTime": now,
        "orders": [line],
        **addr,
    }
    return payload


def push_co_order_to_km(order_id: int, *, co_store) -> dict[str, Any]:
    """审核通过后推送到快麦待发货队列。"""
    if not km_co_enabled():
        return {"success": False, "skipped": True, "error": "快麦客户单推单未配置"}

    order = co_store.get_order(int(order_id))
    if not order:
        return {"success": False, "error": "订单不存在"}

    if (order.get("km_push_status") or "") == "pushed" and (order.get("km_sid") or ""):
        return {"success": True, "item": order, "msg": "已推送过快麦"}

    if (order.get("status") or "") not in ("paid",):
        return {"success": False, "error": "仅「已付款」订单可推快麦，请先完成微信支付"}

    try:
        payload = build_km_trade_payload(order, co_store=co_store)
    except ValueError as e:
        co_store.update_order_km_fields(
            int(order_id),
            km_push_status="failed",
            km_push_error=str(e),
        )
        return {"success": False, "error": str(e)}

    km_api.km_ensure_session()
    res = km_api.km_trade_create_new(payload)
    if not res.get("success"):
        err = res.get("msg") or res.get("error") or json.dumps(res, ensure_ascii=False)[:300]
        co_store.update_order_km_fields(
            int(order_id),
            km_tid=payload["tid"],
            km_user_id=km_co_shop_user_id(),
            km_push_status="failed",
            km_push_error=str(err),
        )
        return {"success": False, "error": err, "km_response": res}

    km_sid = str(res.get("sid") or "").strip()
    if not km_sid:
        trade_list = res.get("tradeList") or res.get("trades") or []
        if isinstance(trade_list, list) and trade_list:
            km_sid = str((trade_list[0] or {}).get("sid") or "").strip()

    item = co_store.update_order_km_fields(
        int(order_id),
        km_tid=payload["tid"],
        km_sid=km_sid,
        km_user_id=km_co_shop_user_id(),
        km_push_status="pushed",
        km_push_error="",
        km_pushed_at=True,
        status="in_production",
    )
    return {"success": True, "item": item, "km_sid": km_sid, "km_response": res}


def apply_km_trade_to_co_order(trade: dict, *, co_store) -> bool:
    """快麦 webhook / 轮询：发货信息回写 co_order。"""
    tid = str(trade.get("tid") or "").strip()
    if not tid:
        return False
    if not _trade_is_shipped(trade):
        return False

    order = co_store.get_order_by_km_tid(tid)
    if not order:
        return False
    if (order.get("status") or "") == "completed" and (order.get("express_no") or ""):
        return False

    company, no = _trade_express(trade)
    if not no:
        return False

    co_store.update_order_km_fields(
        int(order["id"]),
        express_company=company,
        express_no=no,
        status="completed",
        km_sid=str(trade.get("sid") or order.get("km_sid") or "").strip(),
    )
    return True


def sync_pending_shipments(*, co_store, limit: int = 30) -> dict[str, Any]:
    """轮询已推快麦、尚未完成的客户单，补拉物流单号。"""
    report: dict[str, Any] = {"checked": 0, "updated": 0, "errors": []}
    if not km_co_enabled():
        return {**report, "skipped": True}

    pending = co_store.list_orders_pending_km_shipment(limit=limit)
    if not pending:
        return report

    km_api.km_ensure_session()
    end = datetime.now()
    start = end - timedelta(days=30)

    for order in pending:
        tid = (order.get("km_tid") or order.get("order_no") or "").strip()
        if not tid:
            continue
        report["checked"] += 1
        try:
            res = km_api.km_outstock_simple_page(
                start_time=start.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end.strftime("%Y-%m-%d %H:%M:%S"),
                page_no=1,
                page_size=20,
                tid=tid,
            )
            batch = km_api._response_trade_list(res)
            if not batch:
                continue
            if apply_km_trade_to_co_order(batch[0], co_store=co_store):
                report["updated"] += 1
        except Exception as ex:
            report["errors"].append(f"{tid}: {ex}")

    return report
