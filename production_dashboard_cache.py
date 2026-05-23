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

_CACHE_TTL = float(os.getenv("PROD_DASH_CACHE_TTL_SEC", "300"))


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


def _order_type_to_dimoldb_pt(order_type: str) -> str:
    ot = (order_type or "").strip()
    if ot in ("扣底盒", "双插盒", "koudi", "shuangcha"):
        return "koudi" if ot in ("扣底盒", "koudi") else "shuangcha"
    if ot in ("长方形飞机盒", "juxing", "带扣飞机盒", "daikou"):
        return "juxing" if ot in ("长方形飞机盒", "juxing") else "daikou"
    if ot in ("纸箱", "qita"):
        return "qita"
    return "zhengsquare"


def _match_dimoldb_for_line(
    ps: dict[str, Any],
    order_type: str,
    dimoldb_rows: list[dict],
    dm_index: dict | None = None,
    *,
    sku: str = "",
    km_code_index: dict | None = None,
) -> dict[str, Any]:
    """按商家编码或尺寸匹配刀模库。"""
    import km_sku_resolve as ksr

    return ksr.match_dimoldb_for_line(
        ps,
        order_type,
        dimoldb_rows,
        dm_index,
        sku=sku,
        km_code_index=km_code_index,
    )


def rebuild_dashboard_cache(
    *,
    orders_cache_file: str,
    permission_data: dict,
    material_mapping: list[dict],
    load_inventory_fn,
    load_dimoldb_fn=None,
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
    dimoldb_rows: list[dict] = []
    if load_dimoldb_fn:
        try:
            dimoldb_rows = load_dimoldb_fn() or []
        except Exception:
            dimoldb_rows = []
    import dimoldb_store as ds
    import km_sku_map_store as kms
    import km_sku_resolve as ksr

    dm_index = ds.build_dim_match_index(dimoldb_rows) if dimoldb_rows else {}
    km_code_index = ds.build_km_code_index(dimoldb_rows) if dimoldb_rows else {}
    km_index = kms.load_all()

    all_orders: list[dict] = []
    try:
        all_orders = load_cache_orders_fn() or []
    except Exception:
        cache_file = orders_cache_file
        if not os.path.isabs(cache_file):
            cache_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), cache_file
            )
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    all_orders = json.load(f).get("orders", [])
        except Exception:
            all_orders = []

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
            ctx = ksr.resolve_line_context(
                item,
                km_index=km_index,
                material_mapping=material_mapping,
                fetch_if_missing=False,
            )
            raw_attrs = ctx["raw_attrs"]
            sku_code = ctx["sku"]
            if not raw_attrs:
                try:
                    import production_helpers as ph

                    raw_attrs = ph.item_buyer_attrs(item)
                except Exception:
                    pass
            order_qty = int(item.get("qty", 0) or 0)
            item_name = (item.get("name") or "").strip()
            ps = pspec.build_production_spec(
                raw_attrs,
                order_qty,
                title=item_name,
                material_mapping=material_mapping,
            )
            ps = ksr.enrich_production_spec(
                ps,
                ctx.get("km_row"),
                material_mapping=material_mapping,
                order_spec_raw=ctx.get("order_spec_raw") or raw_attrs,
                km_product=ctx.get("km_product"),
                sku=sku_code,
            )
            real_qty = int(ps.get("qty") or order_qty)
            line_type_blob = " ".join(
                x
                for x in (
                    raw_attrs,
                    ps.get("line2") or "",
                    ps.get("material") or "",
                    (ctx.get("km_product") or {}).get("material_hint") or "",
                )
                if x
            )
            line_order_type = mcalc.infer_product_type_for_calc(order_type, line_type_blob)
            has_stock, stock_qty, stock_info = _match_inventory(raw_attrs, real_qty, inv_rows)
            dm_info = _match_dimoldb_for_line(
                ps,
                line_order_type,
                dimoldb_rows,
                dm_index,
                sku=sku_code,
                km_code_index=km_code_index,
            )
            cached_mc = mcalc.get_cached_line(so_id, line_idx)
            mc_status = (cached_mc or {}).get("status") or "pending"
            carton_layer = ps.get("carton_layer") or ""
            if cached_mc and mc_status == "done" and not carton_layer:
                carton_layer = pspec.infer_carton_layer_label(
                    " ".join(
                        x
                        for x in (
                            cached_mc.get("paper_display") or "",
                            cached_mc.get("material") or "",
                            raw_attrs,
                        )
                        if x
                    ),
                    str(cached_mc.get("material") or ""),
                    str(cached_mc.get("material_key") or ""),
                )
            if carton_layer and "层" not in (ps.get("line2") or ""):
                ps = dict(ps)
                ps["carton_layer"] = carton_layer
                ps["material"] = carton_layer
                line2 = pspec._build_formatted_line(
                    diameter_type=ps.get("diameter_type") or "",
                    size=ps.get("size") or "",
                    qty_label=ps.get("qty_label") or "",
                    material=carton_layer,
                    color=ps.get("color") or "",
                )
                ps["line2"] = line2
                ps["formatted"] = line2
                ps["line"] = line2
            if cached_mc and (
                cached_mc.get("dimoldb_code") or cached_mc.get("dimoldb_id")
            ):
                mc_code = (cached_mc.get("dimoldb_code") or "").strip()
                if not mc_code:
                    mc_code = str(cached_mc.get("dimoldb_id") or "").strip()
                dm_info = {
                    **dm_info,
                    "dimoldb_id": cached_mc.get("dimoldb_id") or dm_info.get("dimoldb_id") or "",
                    "dimoldb_code": mc_code or dm_info.get("dimoldb_code") or "",
                    "matched": bool(mc_code or dm_info.get("matched")),
                }
            full_items.append(
                {
                    "name": item.get("name", "") or "",
                    "spec": raw_attrs,
                    "display": ps.get("line2") or ps.get("formatted") or ps.get("line") or "",
                    "platform_attrs": raw_attrs,
                    "platform_spec_raw": ps.get("platform_spec_raw") or raw_attrs,
                    "production_spec": ps.get("line2") or ps.get("formatted") or "",
                    "production_spec_detail": ps,
                    "qty": real_qty,
                    "order_qty": ps.get("order_qty", order_qty),
                    "per_group_qty": ps.get("per_group_qty", 0),
                    "sku": sku_code or item.get("sku", "") or "",
                    "merchant_code": sku_code,
                    "attrs_source": ctx.get("attrs_source") or "order",
                    "dims_source": ps.get("dims_source") or "",
                    "km_dims_missing": bool(ps.get("km_dims_missing")),
                    "km_map_applied": bool(ps.get("km_map_applied")),
                    "km_map_override": bool(ps.get("km_map_override")),
                    "skuId": item.get("skuId", "") or "",
                    "has_stock": has_stock,
                    "stock_qty": stock_qty,
                    "stock_info": stock_info,
                    "dimoldb_id": dm_info.get("dimoldb_id") or "",
                    "dimoldb_code": dm_info.get("dimoldb_code") or "",
                    "dimoldb_matched": bool(dm_info.get("matched")),
                    "dimoldb_skip": bool(dm_info.get("skip")),
                    "material_name": ps.get("material") or "—",
                    "carton_layer_label": carton_layer
                    or (cached_mc or {}).get("carton_layer_label")
                    or "",
                    "material_status": mc_status,
                    "material_calc": cached_mc or {"status": mc_status},
                    "dimensions_ok": bool(ps.get("dimensions_ok")),
                    "dimensions_missing": ps.get("dimensions_missing") or [],
                    "line_index": line_idx,
                    "product_type": line_order_type,
                }
            )

        if full_items:
            if any(
                (fi.get("product_type") or "") == "纸箱"
                or pspec.attrs_indicate_carton(
                    " ".join(
                        x
                        for x in (
                            fi.get("spec") or "",
                            fi.get("production_spec") or "",
                            fi.get("material_name") or "",
                        )
                        if x
                    )
                )
                for fi in full_items
            ):
                order_type = "纸箱"

        addr = o.get("receiver_address", "") or ""
        addr_parts = addr.split() if addr else []
        pi = printed_info.get(so_id, {})

        result.append(
            {
                "so_id": so_id,
                "tid": str(o.get("tid") or o.get("platform_tid") or "").strip(),
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
                "has_stock": any(x.get("has_stock") for x in full_items)
                if full_items
                else False,
                "has_all_stock": all(x.get("has_stock") for x in full_items)
                if full_items
                else False,
                "inventory_matched": any((x.get("stock_qty") or 0) > 0 for x in full_items)
                if full_items
                else False,
                "placeholder_spec": any(
                    (x.get("production_spec_detail") or {}).get("is_placeholder")
                    for x in full_items
                ),
            }
        )

    result.sort(key=lambda x: x.get("created", ""), reverse=True)
    result.sort(key=lambda x: x.get("placeholder_spec", False))
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
        age = now - float(_cache.get("ts") or 0)
        has_orders = bool(_cache.get("orders"))
        if not force and has_orders and age < max_age:
            return _cache
        stale = dict(_cache) if has_orders else None

    if not force and not has_orders:
        def _bg_first() -> None:
            global _cache
            try:
                fresh = rebuild_fn()
                with _cache_lock:
                    _cache = fresh
            except Exception as e:
                with _cache_lock:
                    _cache["error"] = str(e)

        threading.Thread(
            target=_bg_first, daemon=True, name="prod-dash-first-build"
        ).start()
        with _cache_lock:
            return dict(_cache)

    if not force and stale:
        def _bg_refresh() -> None:
            global _cache
            try:
                fresh = rebuild_fn()
                with _cache_lock:
                    _cache = fresh
            except Exception as e:
                with _cache_lock:
                    _cache["error"] = str(e)

        threading.Thread(
            target=_bg_refresh, daemon=True, name="prod-dash-refresh"
        ).start()
        return stale

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


def patch_line_material(
    so_id: str,
    line_index: int,
    mc_result: dict[str, Any],
) -> None:
    """算料后只更新单行，避免整表重建。"""
    with _cache_lock:
        for o in _cache.get("orders") or []:
            if str(o.get("so_id") or "") != str(so_id):
                continue
            for fi in o.get("full_items") or []:
                if int(fi.get("line_index", -1)) != int(line_index):
                    continue
                st = (mc_result or {}).get("status") or "pending"
                fi["material_calc"] = mc_result or {}
                fi["material_status"] = st
                layer = (mc_result or {}).get("carton_layer_label") or ""
                if layer:
                    fi["carton_layer_label"] = layer
                    if "层" not in (fi.get("production_spec") or ""):
                        import production_spec as pspec

                        fi["material_name"] = layer
                        psd = fi.get("production_spec_detail") or {}
                        if psd and not psd.get("carton_layer"):
                            psd = dict(psd)
                            psd["carton_layer"] = layer
                            psd["material"] = layer
                            size = (psd.get("size") or "").strip()
                            diam = (psd.get("diameter_type") or "").strip()
                            qty_label = (psd.get("qty_label") or "").strip()
                            color = (psd.get("color") or "").strip()
                            line2 = pspec._build_formatted_line(
                                diameter_type=diam,
                                size=size,
                                qty_label=qty_label,
                                material=layer,
                                color=color,
                            )
                            psd["line2"] = line2
                            psd["formatted"] = line2
                            psd["line"] = line2
                            fi["production_spec_detail"] = psd
                            fi["production_spec"] = line2
                            fi["display"] = line2
                code = (mc_result or {}).get("dimoldb_code") or ""
                if code:
                    fi["dimoldb_code"] = code
                    fi["dimoldb_matched"] = True
                return
            return


def find_order_in_cache(so_id: str) -> dict | None:
    with _cache_lock:
        for o in _cache.get("orders") or []:
            if o.get("so_id") == so_id:
                return o
    return None
