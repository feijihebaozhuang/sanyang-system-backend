# -*- coding: utf-8 -*-
"""打单管理列表缓存：后台构建，接口分页返回，避免每次请求全量重算。"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any

_cache_lock = threading.Lock()
_cache: dict[str, Any] = {
    "ts": 0.0,
    "orders": [],
    "printed_info": {},
    "shops": [],
    "types": [],
    "error": "",
}

_CACHE_TTL = 90


def _inv_index(inventory_list: list[dict]) -> list[tuple[float, float, float, int, str]]:
    rows: list[tuple[float, float, float, int, str]] = []
    for inv in inventory_list:
        try:
            rows.append(
                (
                    float(inv.get("length", 0) or 0),
                    float(inv.get("width", 0) or 0),
                    float(inv.get("height", 0) or 0),
                    int(inv.get("qty", 0) or 0),
                    inv.get("name", "") or "",
                )
            )
        except (TypeError, ValueError):
            continue
    return rows


def _match_inventory(
    spec_str: str, need_qty: int, inv_rows: list[tuple[float, float, float, int, str]]
) -> tuple[bool, int, str]:
    spec = spec_str or ""
    dim_m = re.search(r"(\d+[\.\d]*)\s*[*×xX]\s*(\d+[\.\d]*)", spec)
    if not dim_m:
        return False, 0, "无法解析尺寸"
    l, w = float(dim_m.group(1)), float(dim_m.group(2))
    h_m = re.search(r"(?:高|高度)[【】]?(\d+[\.\d]*)", spec)
    if not h_m:
        h_m = re.search(r"(\d+[\.\d]*)cm高", spec)
    h = float(h_m.group(1)) if h_m else 0.0
    best_qty = 0
    best_name = ""
    for inv_l, inv_w, inv_h, inv_qty, inv_name in inv_rows:
        if abs(inv_l - l) <= 0.5 and abs(inv_w - w) <= 0.5:
            if h == 0 or abs(inv_h - h) <= 0.5:
                if inv_qty > best_qty:
                    best_qty = inv_qty
                    best_name = inv_name
    if best_qty > 0:
        return best_qty >= need_qty, best_qty, f"{best_name} 库存{best_qty}"
    return False, 0, "无匹配库存"


def rebuild_dashboard_cache(
    *,
    orders_cache_file: str,
    permission_data: dict,
    material_mapping: list[dict],
    load_inventory_fn,
    load_cache_orders_fn,
    get_db_fn,
    infer_order_type_fn,
    internal_order_id_fn,
    parse_flow_steps_fn,
    template_steps_fn,
    normalize_shop_fn,
) -> dict[str, Any]:
    """构建全量打单列表（供分页切片）。"""
    import material_calc as mcalc
    import production_spec as pspec

    printed_info: dict[str, dict] = {}
    flow_map: dict[str, dict] = {}
    try:
        db = get_db_fn()
        cur = db.cursor()
        cur.execute(
            "SELECT order_id, created_at, printed_by FROM print_logs WHERE status='printed'"
        )
        for r in cur.fetchall():
            oid = r["order_id"]
            printed_info[oid] = {
                "time": r["created_at"],
                "by": r["printed_by"] or "",
            }
        cur.execute("SELECT * FROM production_flows")
        for r in cur.fetchall():
            flow_map[r["order_id"]] = r
        cur.close()
        db.close()
    except Exception:
        pass

    printed_ids = set(printed_info.keys())
    inventory_data = load_inventory_fn()
    inv_rows = _inv_index(inventory_data.get("finished", []))

    all_orders: list[dict] = []
    try:
        cache_file = orders_cache_file
        if not os.path.isabs(cache_file):
            cache_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), cache_file
            )
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                all_orders = json.load(f).get("orders", [])
    except Exception:
        all_orders = load_cache_orders_fn() or []

    process_tree = permission_data.get("processes", [])
    shops: set[str] = set()
    types: set[str] = set()
    result: list[dict] = []

    for o in all_orders:
        so_id = internal_order_id_fn(o)
        order_type = infer_order_type_fn(o)
        try:
            shop = normalize_shop_fn(o.get("shop_name", "") or "")
        except Exception:
            shop = (o.get("shop_name") or "").strip() or "未知店铺"
        created_date = (o.get("created") or "")[:10]
        shops.add(shop)
        types.add(order_type)

        flow = flow_map.get(so_id)
        progress = 0
        steps: list[dict] = []
        if flow:
            parsed = parse_flow_steps_fn(flow.get("steps_json"))
            total_s = flow.get("total_steps", 0) or len(parsed)
            done_n = sum(1 for s in parsed if s.get("done"))
            progress = round(done_n / total_s * 100) if total_s > 0 else 0
            for i, s in enumerate(parsed):
                steps.append(
                    {
                        "name": s.get("step") or s.get("name"),
                        "done": bool(s.get("done")),
                        "active": (not s.get("done")) and i == done_n,
                    }
                )
        else:
            template = template_steps_fn(process_tree, order_type)
            for i, s in enumerate(template):
                steps.append(
                    {
                        "name": s.get("step") or "",
                        "done": False,
                        "active": i == 0,
                    }
                )

        full_items = []
        for line_idx, item in enumerate(o.get("items") or []):
            if not isinstance(item, dict):
                continue
            raw_attrs = (
                item.get("display")
                or item.get("platform_attrs")
                or item.get("spec")
                or ""
            ).strip()
            attrs = pspec.sanitize_sku_attrs(raw_attrs) or raw_attrs
            qty = int(item.get("qty", 0) or 0)
            has_stock, stock_qty, stock_info = _match_inventory(attrs, qty, inv_rows)
            ps = pspec.build_production_spec(
                attrs, qty, material_mapping=material_mapping or []
            )
            cached_mc = mcalc.get_cached_line(so_id, line_idx)
            mc_status = (cached_mc or {}).get("status") or "pending"
            full_items.append(
                {
                    "name": item.get("name", "") or "",
                    "spec": attrs,
                    "display": attrs,
                    "platform_attrs": attrs,
                    "production_spec": ps.get("line", "") or "",
                    "production_spec_detail": ps,
                    "qty": qty,
                    "sku": item.get("sku", "") or "",
                    "skuId": item.get("skuId", "") or "",
                    "has_stock": has_stock,
                    "stock_qty": stock_qty,
                    "stock_info": stock_info,
                    "material_name": ps.get("material") or "—",
                    "material_status": mc_status,
                    "material_calc": cached_mc or {"status": mc_status},
                    "line_index": line_idx,
                }
            )

        addr = o.get("receiver_address", "") or ""
        addr_parts = addr.split() if addr else []
        pi = printed_info.get(so_id, {})

        result.append(
            {
                "so_id": so_id,
                "shop": shop,
                "province": addr_parts[0] if addr_parts else "",
                "created": created_date,
                "product_name": ((o.get("items") or [{}])[0].get("name", "") or ""),
                "product_type": order_type,
                "full_items": full_items,
                "qty": sum(i.get("qty", 0) for i in full_items),
                "seller_memo": o.get("seller_memo", "") or "",
                "buyer_memo": o.get("buyer_memo", "") or "",
                "printed": so_id in printed_ids,
                "printed_at": pi.get("time", ""),
                "printed_by": pi.get("by", ""),
                "has_flow": flow is not None,
                "flow_status": flow.get("status", "") if flow else "",
                "receiver": o.get("receiver_name", ""),
                "address": addr,
                "phone": o.get("receiver_phone", "")
                or o.get("receiver_mobile", ""),
                "progress": progress,
                "steps": steps,
                "has_all_stock": all(x.get("has_stock") for x in full_items)
                if full_items
                else False,
            }
        )

    result.sort(key=lambda x: x.get("created", ""), reverse=True)
    return {
        "ts": time.time(),
        "orders": result,
        "printed_info": printed_info,
        "shops": sorted(shops),
        "types": sorted(types),
        "error": "",
    }


def get_dashboard_cache(
    rebuild_fn,
    *,
    force: bool = False,
    max_age: float = _CACHE_TTL,
) -> dict[str, Any]:
    global _cache
    now = time.time()
    with _cache_lock:
        if (
            not force
            and _cache.get("orders")
            and now - float(_cache.get("ts") or 0) < max_age
        ):
            return _cache
    try:
        fresh = rebuild_fn()
        with _cache_lock:
            _cache = fresh
        return fresh
    except Exception as e:
        with _cache_lock:
            _cache["error"] = str(e)
        return _cache


def invalidate_dashboard_cache() -> None:
    with _cache_lock:
        _cache["ts"] = 0.0


def find_order_in_cache(so_id: str) -> dict | None:
    with _cache_lock:
        for o in _cache.get("orders") or []:
            if o.get("so_id") == so_id:
                return o
    return None
