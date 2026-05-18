# -*- coding: utf-8 -*-
"""1688 开放平台直连拉单（无需奇门，与快麦 1688 店铺互补）。"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from typing import Any, Callable

try:
    from settings import ALIBABA_SHOPS
except Exception:
    ALIBABA_SHOPS = []

from km_api import km_platform_item_attrs


def alibaba_configured() -> bool:
    return bool(ALIBABA_SHOPS)


def _sign(url_path: str, params: dict, secret: str) -> str:
    param_list = sorted([str(k) + str(v) for k, v in params.items()])
    msg = url_path.encode("utf-8")
    for p in param_list:
        msg += p.encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha1).hexdigest().upper()


def fetch_all_shops_orders(
    *,
    max_pages: int = 5,
    page_size: int = 50,
    order_status: str = "waitsellersend",
) -> list[dict]:
    """遍历 ALIBABA_SHOPS 拉待发货订单，返回原始 1688 订单结构列表。"""
    if not ALIBABA_SHOPS:
        return []

    api = "1/com.alibaba.trade/alibaba.trade.getSellerOrderList"
    all_orders: list[dict] = []

    for shop in ALIBABA_SHOPS:
        shop_name = shop.get("shop_name") or ""
        token = shop.get("access_token") or ""
        app_key = int(shop.get("app_key") or 0)
        app_secret = shop.get("app_secret") or ""
        server = shop.get("server") or "gw.open.1688.com"
        if not token or not app_key or not app_secret:
            continue

        print(f"[1688直连] 拉取: {shop_name}")
        for page in range(1, max_pages + 1):
            try:
                url_path = f"param2/{api}/{app_key}"
                params: dict[str, Any] = {
                    "access_token": token,
                    "page": page,
                    "pageSize": page_size,
                    "orderStatus": order_status,
                }
                params["_aop_signature"] = _sign(url_path, params, app_secret)
                url = f"https://{server}/openapi/{url_path}"
                req = urllib.request.Request(
                    url,
                    data=urllib.parse.urlencode(params).encode("utf-8"),
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                orders = data.get("result") or []
                if not isinstance(orders, list) or not orders:
                    break
                for o in orders:
                    if isinstance(o, dict):
                        info = o.setdefault("baseInfo", o.get("baseInfo") or {})
                        if isinstance(info, dict):
                            info["shop_name"] = shop_name
                all_orders.extend(orders)
                if len(orders) < page_size:
                    break
                time.sleep(0.35)
            except Exception as e:
                print(f"[1688直连] {shop_name} 第{page}页失败: {e}")
                break
    return all_orders


def format_order(o: dict, memo_getter: Callable[[str], str] | None = None) -> dict:
    """1688 原始单 → orders_cache 统一结构。"""
    info = o.get("baseInfo") or {}
    items = o.get("productItems") or []
    product_list = []
    for item in items:
        if not isinstance(item, dict):
            continue
        attrs = km_platform_item_attrs(item)
        product_list.append(
            {
                "name": item.get("name", ""),
                "sku": item.get("productCargoNumber", ""),
                "qty": item.get("quantity", 0),
                "price": item.get("price", 0),
                "spec": attrs,
                "display": attrs,
                "platform_attrs": attrs,
                "skuId": item.get("skuID", ""),
                "productId": item.get("productID", ""),
            }
        )
    so_id = str(info.get("idOfStr") or info.get("id") or "")
    memo_fn = memo_getter or (lambda _x: "")
    shop_full = info.get("shop_name") or ""
    st = info.get("status", "") or ""
    status_label = "待发货" if st == "waitsellersend" else (st or "待发货")
    order = {
        "so_id": so_id,
        "tid": so_id,
        "platform": "1688",
        "platform_label": "1688",
        "source": "1688",
        "order_status": st,
        "status_label": status_label,
        "status": status_label,
        "created": (info.get("createTime") or "")[:10],
        "pay_time": (info.get("payTime") or "")[:10],
        "total_amount": info.get("totalAmount", 0),
        "shipping_fee": (info.get("shippingFee", 0) or 0) / 100,
        "discount": (info.get("discount", 0) or 0) / 100,
        "receiver_name": info.get("receiverName") or info.get("buyerLoginId", ""),
        "receiver_mobile": info.get("receiverMobile", ""),
        "receiver_address": info.get("receiverAddress", ""),
        "receiver_phone": info.get("receiverPhone", ""),
        "shop_name": shop_full,
        "items": product_list,
        "buyer_login_id": info.get("buyerLoginId", ""),
        "alipay_trade_id": info.get("alipayTradeId", ""),
        "trade_type": info.get("tradeType", ""),
        "buyer_memo": "",
        "seller_memo": memo_fn(so_id),
        "sync_source": "1688_api",
    }
    try:
        import km_api as _km

        return _km.finalize_cache_order(order)
    except Exception:
        return order
