# -*- coding: utf-8 -*-
"""快麦 Webhook 回调：验签、解析订单、写入 MySQL order_cache。"""
from __future__ import annotations

import json
from typing import Any

import km_api
import order_cache_store as ocs
import order_sync as osync


def _flatten_params(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in data.items():
        if v is None or k == "sign":
            continue
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        else:
            out[k] = v
    return out


def verify_kuaimai_sign(params: dict[str, Any]) -> bool:
    sign = (params.get("sign") or "").strip()
    if not sign:
        return False
    secret = km_api.km_app_secret()
    if not secret:
        return False
    method = (params.get("sign_method") or params.get("signMethod") or "hmac").strip()
    flat = _flatten_params(params)
    expected = km_api.km_sign(flat, secret, method)
    return expected == sign.upper() or expected == sign


def _extract_trades(body: dict[str, Any]) -> list[dict]:
    trades: list[dict] = []
    for key in ("trades", "tradeList", "orders", "orderList", "data", "trade"):
        val = body.get(key)
        if isinstance(val, list):
            trades.extend(x for x in val if isinstance(x, dict))
        elif isinstance(val, dict):
            inner = val.get("trades") or val.get("tradeList") or val.get("orders")
            if isinstance(inner, list):
                trades.extend(x for x in inner if isinstance(x, dict))
            else:
                trades.append(val)
    if not trades and body.get("tid"):
        trades.append(body)
    return trades


def apply_webhook_payload(body: dict[str, Any]) -> dict[str, Any]:
    """处理快麦推送，更新 MySQL 缓存。返回处理报告。"""
    report: dict[str, Any] = {"upserted": 0, "removed": 0, "errors": []}
    if not body:
        return {**report, "msg": "empty body"}

    params = dict(body)
    if body.get("sign") and not verify_kuaimai_sign(params):
        return {**report, "success": False, "msg": "sign invalid"}

    shops = km_api.km_shop_lookup()
    orders: list[dict] = []
    for trade in _extract_trades(body):
        try:
            o = km_api.km_trade_to_cache_order(trade, shops)
            o["shop_name"] = osync.normalize_shop_display(o.get("shop_name") or "")
            o["sync_source"] = "kuaimai_webhook"
            km_api.finalize_cache_order(o)
            orders.append(o)
        except Exception as ex:
            report["errors"].append(str(ex))

    pending = [o for o in orders if osync._is_pending_cache_order(o)]
    removed = [o for o in orders if o not in pending]
    for o in pending:
        try:
            ocs.upsert_order(o)
            report["upserted"] += 1
        except Exception as ex:
            report["errors"].append(f"upsert {o.get('so_id')}: {ex}")
    for o in removed:
        sid = str(o.get("so_id") or "").strip()
        if sid and ocs.delete_order(sid):
            report["removed"] += 1

    if pending:
        try:
            all_orders = ocs.read_orders_mysql(finalize=False)
            stats = ocs.compute_dashboard_stats(all_orders)
            ocs.write_stats_cache("dashboard_summary", stats)
        except Exception as ex:
            report["errors"].append(f"stats: {ex}")

    return {**report, "success": True}


def subscribe_webhook(callback_url: str, *, event_types: str = "trade") -> dict[str, Any]:
    """调用快麦 erp.webhook.subscribe 注册回调（需平台侧开通）。"""
    if not km_api.km_configured():
        return {"success": False, "msg": "快麦未配置"}
    km_api.km_ensure_session()
    biz: dict[str, Any] = {"url": callback_url}
    if event_types:
        biz["event"] = event_types
        biz["eventType"] = event_types
    return km_api.km_request("erp.webhook.subscribe", biz)
