# -*- coding: utf-8 -*-
"""订单子单：商家编码 → 快麦映射 → 生产规格 / 刀模。"""
from __future__ import annotations

from typing import Any

import km_sku_map_store as kms


def item_merchant_code(item: dict[str, Any]) -> str:
    for key in ("sku", "outerId", "sysOuterId", "merchant_code"):
        v = (item.get(key) or "").strip()
        if v:
            return v
    return ""


def item_raw_attrs(item: dict[str, Any]) -> str:
    for key in (
        "platform_spec_raw",
        "platform_attrs",
        "display",
        "spec",
    ):
        v = (item.get(key) or "").strip()
        if v:
            return v
    try:
        import production_helpers as ph

        return (ph.item_buyer_attrs(item) or "").strip()
    except Exception:
        return ""


def resolve_line_context(
    item: dict[str, Any],
    *,
    km_index: dict[str, dict] | None = None,
    material_mapping: list[dict] | None = None,
) -> dict[str, Any]:
    """
    解析子单上下文：优先订单买家属性；缺尺寸时用快麦映射补。
    返回 raw_attrs, sku, km_row, attrs_source。
    """
    del material_mapping  # 预留
    sku = item_merchant_code(item)
    raw = item_raw_attrs(item)
    km_row = kms.lookup_outer_id(sku, km_index) if sku else None
    source = "order"

    if km_row:
        alias = (km_row.get("spec_alias") or "").strip()
        if not raw and alias:
            raw = alias
            source = "km_map_alias"
        elif raw and alias:
            import production_spec as pspec

            dims = pspec.parse_dimensions_for_item(raw)
            if not pspec.dimensions_ready_for_calc(dims) and alias:
                raw = alias
                source = "km_map_fallback"

    return {
        "raw_attrs": raw,
        "sku": sku,
        "km_row": km_row,
        "attrs_source": source,
    }


def enrich_production_spec(
    ps: dict[str, Any],
    km_row: dict[str, Any] | None,
    *,
    material_mapping: list[dict] | None = None,
) -> dict[str, Any]:
    """映射表补全 production_spec 中缺失的长宽高/材料。"""
    if not km_row:
        return ps
    import production_spec as pspec

    out = dict(ps)
    if out.get("dimensions_ok"):
        return out

    l, w, h = kms.production_dims_from_map(km_row)
    if not (l and w):
        return out

    diam = (km_row.get("dim_kind") or "").strip()
    if diam == "inner":
        diam_label = "内径"
    elif diam == "outer":
        diam_label = "外径"
    else:
        diam_label = out.get("diameter_type") or ""

    mat = (km_row.get("material") or "").strip()
    if not mat:
        mat = out.get("material") or ""
    if not mat and km_row.get("spec_alias"):
        mat = pspec.match_production_material(
            km_row["spec_alias"], material_mapping
        ) or ""

    size = pspec.format_size_compact({"l": l, "w": w, "h": h or 0})
    qty_label = out.get("qty_label") or ""
    color = out.get("color") or ""
    line2 = pspec._build_formatted_line(
        diameter_type=diam_label,
        size=size,
        qty_label=qty_label,
        material=mat,
        color=color,
    )

    out.update(
        {
            "length": l,
            "width": w,
            "height": h or out.get("height"),
            "dimensions_ok": True,
            "dimensions_missing": [],
            "material": mat or out.get("material"),
            "diameter_type": diam_label or out.get("diameter_type"),
            "size": size,
            "line2": line2 or out.get("line2"),
            "formatted": line2 or out.get("formatted"),
            "line": line2 or out.get("line"),
            "km_map_applied": True,
        }
    )
    return out


def _order_type_to_dimoldb_pt(order_type: str) -> str:
    ot = (order_type or "").strip()
    if ot in ("扣底盒", "双插盒", "koudi", "shuangcha"):
        return "koudi" if ot in ("扣底盒", "koudi") else "shuangcha"
    if ot in ("长方形飞机盒", "juxing", "带扣飞机盒", "daikou"):
        return "juxing" if ot in ("长方形飞机盒", "juxing") else "daikou"
    if ot in ("纸箱", "qita"):
        return "qita"
    return "zhengsquare"


def _match_dimoldb_by_dimensions(
    ps: dict[str, Any],
    order_type: str,
    dimoldb_rows: list[dict],
    dm_index: dict | None = None,
) -> dict[str, Any]:
    """按尺寸匹配刀模库。"""
    import dimoldb_store as ds
    import material_calc as mcalc

    attrs = ps.get("platform_spec_raw") or ""
    if mcalc._is_carton_product(order_type, attrs):
        return {"skip": True, "matched": False, "dimoldb_id": "", "dimoldb_code": ""}
    l, w, h = ps.get("length"), ps.get("width"), ps.get("height")
    if not l or not w:
        return {"skip": False, "matched": False, "dimoldb_id": "", "dimoldb_code": ""}
    best_row: dict[str, Any] | None = None
    if dimoldb_rows:
        if dm_index is None:
            dm_index = ds.build_dim_match_index(dimoldb_rows)
        fake_item = {
            "length": l,
            "width": w,
            "height": h or 0,
            "product_type": _order_type_to_dimoldb_pt(order_type),
        }
        hits = ds.match_dimoldb_for_inventory_item(
            fake_item, dm_index, infer_fn=ds.infer_type_class
        )
        if hits:
            best_row = hits[0]
    if not best_row:
        dm = mcalc.match_dimoldb(
            float(l),
            float(w),
            float(h or 0),
            dimoldb_rows or [],
            order_type,
        )
        if dm.get("success"):
            best_row = dm.get("row") or {}
            code = (dm.get("code") or dm.get("display_code") or "").strip()
            return {
                "skip": False,
                "matched": True,
                "dimoldb_id": dm.get("dimoldb_id") or "",
                "dimoldb_code": code or str(dm.get("dimoldb_id") or ""),
            }
        return {"skip": False, "matched": False, "dimoldb_id": "", "dimoldb_code": ""}
    code = (best_row.get("code") or "").strip() or str(best_row.get("id") or "")
    return {
        "skip": False,
        "matched": True,
        "dimoldb_id": str(best_row.get("id") or ""),
        "dimoldb_code": code,
    }


def match_dimoldb_for_line(
    ps: dict[str, Any],
    order_type: str,
    dimoldb_rows: list[dict],
    dm_index: dict | None,
    *,
    sku: str = "",
    km_code_index: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """商家编码优先匹配刀模，其次尺寸匹配。"""
    import dimoldb_store as ds
    import material_calc as mcalc

    code = (sku or "").strip()
    if code and km_code_index is None and dimoldb_rows:
        km_code_index = ds.build_km_code_index(dimoldb_rows)
    if code and km_code_index:
        dm = km_code_index.get(code) or km_code_index.get(code.lower())
        if dm:
            display = mcalc.dimoldb_display_code(dm)
            return {
                "skip": False,
                "matched": True,
                "dimoldb_id": str(dm.get("id") or ""),
                "dimoldb_code": display or str(dm.get("id") or ""),
                "match_source": "km_mapping_code",
            }

    info = _match_dimoldb_by_dimensions(ps, order_type, dimoldb_rows, dm_index)
    if info.get("matched"):
        info["match_source"] = "dimensions"
    return info
