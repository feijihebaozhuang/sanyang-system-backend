# -*- coding: utf-8 -*-
"""聚水潭API封装：签名/商品上传/库存查询（新API openapi.jushuitan.com）。"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

import requests

_JST_APP_KEY = os.getenv("JST_APP_KEY", "").strip()
_JST_APP_SECRET = os.getenv("JST_APP_SECRET", "").strip()
_JST_ACCESS_TOKEN = os.getenv("JST_ACCESS_TOKEN", "").strip()
_JST_API_URL = os.getenv("JST_API_URL_NEW", "https://openapi.jushuitan.com").strip()


def _sign(params: dict[str, str]) -> str:
    """聚水潭新API签名：MD5(secret + key1value1key2value2...)"""
    sorted_keys = sorted(k for k in params if k != "sign")
    raw = _JST_APP_SECRET + "".join(f"{k}{params[k]}" for k in sorted_keys)
    return hashlib.md5(raw.encode()).hexdigest()


def _request(path: str, biz: dict[str, Any] | None = None) -> dict[str, Any]:
    """通用请求。path如 /open/shops/query"""
    if not (_JST_APP_KEY and _JST_APP_SECRET and _JST_ACCESS_TOKEN):
        return {"code": -1, "msg": "聚水潭未配置（JST_APP_KEY/SECRET/ACCESS_TOKEN）"}
    ts = str(int(time.time()))
    biz_str = json.dumps(biz or {}, ensure_ascii=False)
    payload = {
        "access_token": _JST_ACCESS_TOKEN,
        "app_key": _JST_APP_KEY,
        "biz": biz_str,
        "charset": "utf-8",
        "timestamp": ts,
        "version": "2",
    }
    payload["sign"] = _sign(payload)
    url = f"{_JST_API_URL}{path}"
    try:
        r = requests.post(url, data=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def configured() -> bool:
    return bool(_JST_APP_KEY and _JST_APP_SECRET and _JST_ACCESS_TOKEN)


# ---------- 查询接口 ----------


def shops_query() -> list[dict]:
    """店铺列表。"""
    res = _request("/open/shops/query")
    if res.get("code") != 0:
        return []
    return (res.get("data") or {}).get("datas") or []


def inventory_query(
    *,
    sku_ids: str = "",
    modified_begin: str = "",
    modified_end: str = "",
    page_index: int = 1,
    page_size: int = 100,
) -> list[dict]:
    """库存查询。"""
    biz: dict[str, Any] = {
        "page_index": page_index,
        "page_size": min(page_size, 200),
    }
    if sku_ids:
        biz["sku_ids"] = sku_ids
    if modified_begin and modified_end:
        biz["modified_begin"] = modified_begin
        biz["modified_end"] = modified_end
    res = _request("/open/inventory/query", biz)
    if res.get("code") != 0:
        return []
    return (res.get("data") or {}).get("inventorys") or []


def sku_query(
    *,
    sku_ids: str = "",
    modified_begin: str = "",
    modified_end: str = "",
    page_index: int = 1,
    page_size: int = 100,
) -> list[dict]:
    """普通商品资料查询（按sku编码）。"""
    biz: dict[str, Any] = {
        "page_index": page_index,
        "page_size": min(page_size, 200),
    }
    if sku_ids:
        biz["sku_ids"] = sku_ids
    if modified_begin and modified_end:
        biz["modified_begin"] = modified_begin
        biz["modified_end"] = modified_end
    res = _request("/open/sku/query", biz)
    if res.get("code") != 0:
        return []
    return (res.get("data") or {}).get("datas") or []


# ---------- 写入接口 ----------


def upload_items(items: list[dict]) -> dict[str, Any]:
    """批量上传商品资料到聚水潭。
    
    items每项格式:
        i_id: str  唯一的商品款式编码（必填）
        sku_id: str  商家编码（必填）
        name: str  商品名
        item_type: str  成品/半成品/原材料/包材
        unit: str  单位（默认个）
        category_id: int  分类ID（0=不指定）
        stock_enabled: bool
        sale_price: float  售价
        cost_price: float  成本价
        weight: float  重量(kg)
        spec: list[{"name":"尺寸","value":"10*10*5"}, ...]
    """
    if not items:
        return {"code": -1, "msg": "items 为空"}
    biz = {"items": items}
    return _request("/open/jushuitan/itemsku/upload", biz)


def upload_items_batch(items: list[dict]) -> dict[str, Any]:
    """批量上传商品（备用接口）。"""
    if not items:
        return {"code": -1, "msg": "items 为空"}
    biz = {"items": items}
    return _request("/open/webapi/itemapi/itemsku/itemskubatchupload", biz)


# ---------- 快麦→聚水潭 转换 ----------


def km_map_row_to_jst_item(
    row: dict[str, Any],
    *,
    i_id_prefix: str = "KM_",
) -> dict[str, Any] | None:
    """将 km_sku_map 的一条记录转为聚水潭上传格式。"""
    outer_id = (row.get("outer_id") or "").strip()
    if not outer_id:
        return None
    spec_alias = (row.get("spec_alias") or "").strip()
    km_title = (row.get("km_title") or "").strip()
    name = km_title or spec_alias or outer_id

    l = float(row.get("length") or 0)
    w = float(row.get("width") or 0)
    h = float(row.get("height") or 0)
    mat = (row.get("material") or "").strip()
    pt = (row.get("product_type") or "juxing").strip()

    # 构建规格数组
    spec: list[dict] = []
    if l and w:
        size_str = f"{l}x{w}"
        if h:
            size_str += f"x{h}"
        spec.append({"name": "尺寸", "value": size_str})
    if mat:
        spec.append({"name": "材质", "value": mat})
    if pt:
        type_label = {"zhengsquare": "正方形", "juxing": "长方形", "daikou": "带扣"}.get(pt, pt)
        spec.append({"name": "类型", "value": type_label})
    if spec_alias:
        spec.append({"name": "规格别名", "value": spec_alias})

    i_id = f"{i_id_prefix}{outer_id}"[:50]

    return {
        "i_id": i_id,
        "sku_id": outer_id,
        "name": name[:200],
        "item_type": "成品",
        "unit": "个",
        "category_id": 0,
        "stock_enabled": True,
        "spec": spec,
        "cost_price": 0,
        "sale_price": 0,
        "weight": 0,
    }
