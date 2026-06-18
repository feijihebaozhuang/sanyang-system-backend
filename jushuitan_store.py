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
    i_id_prefix: str = "",  # 默认去掉前缀，直接用outer_id
) -> dict[str, Any] | None:
    """将 km_sku_map 的一条记录转为聚水潭上传格式。

    字段映射（根据快麦导出表 vs 聚水潭商品资料导出表）：
      快麦主商家编码 → 聚水潭商品编码(sku_id)
      快麦商品名称 → 聚水潭款式编码(i_id)
      快麦商品简称 → 聚水潭商品简称(short_name)
      快麦执行标准 → 聚水潭商品名称(name)
      快麦商品备注 → 聚水潭备注(remark)
      快麦重量/长/宽/高 → 对应字段
    """
    outer_id = (row.get("outer_id") or "").strip()
    if not outer_id:
        return None

    # 快麦字段取值
    km_title = (row.get("km_title") or "").strip()       # 快麦商品名称
    km_short_name = (row.get("km_short_name") or "").strip()  # 快麦商品简称
    exec_std = (row.get("exec_standard") or "").strip()  # 快麦执行标准
    remark = (row.get("remark") or "").strip()            # 快麦商品备注

    l = float(row.get("x") or row.get("length") or 0)
    w = float(row.get("y") or row.get("width") or 0)
    h = float(row.get("z") or row.get("height") or 0)
    wt = float(row.get("weight") or 0)

    # 聚水潭款式编码(i_id) = 快麦商品名称
    i_id_val = km_title or outer_id

    # 聚水潭商品名称(name) = 快麦执行标准
    name_val = exec_std or km_title or outer_id

    # 聚水潭商品简称(short_name) = 快麦商品简称
    short_val = km_short_name or ""

    # 构建规格数组（商品备注/尺寸等作为规格展示，但对于聚水潭来说不是必要）
    spec: list[dict] = []
    mat = (row.get("material") or "").strip()
    if mat:
        spec.append({"name": "材质", "value": mat})
    pt = (row.get("product_type") or "juxing").strip()
    if pt:
        type_label = {"zhengsquare": "正方形", "juxing": "长方形", "daikou": "带扣"}.get(pt, pt)
        spec.append({"name": "类型", "value": type_label})
    spec_alias = (row.get("spec_alias") or "").strip()
    if spec_alias:
        spec.append({"name": "规格别名", "value": spec_alias})

    i_id = f"{i_id_prefix}{i_id_val}"[:50]

    result = {
        "i_id": i_id,
        "sku_id": outer_id,
        "name": name_val[:200],
        "short_name": short_val[:100],
        "item_type": "成品",
        "unit": "个",
        "category_id": 0,
        "stock_enabled": True,
        "spec": spec,
        "cost_price": 0,
        "sale_price": 0,
        "weight": wt,
    }
    if remark:
        result["remark"] = remark[:200]
    # 长宽高（聚水潭字段名：长/宽/高）
    if l:
        result["pkg_length"] = l
    if w:
        result["pkg_width"] = w
    if h:
        result["pkg_height"] = h

    return result
