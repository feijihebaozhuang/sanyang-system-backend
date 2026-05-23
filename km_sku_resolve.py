# -*- coding: utf-8 -*-
"""订单子单：快麦商品档案尺寸 → 生产规格 / 刀模（不猜买家规格文本）。"""
from __future__ import annotations

from typing import Any

import km_api
import km_sku_map_store as kms


def item_merchant_code(item: dict[str, Any]) -> str:
    return km_api.km_line_merchant_code(item)


def item_raw_attrs(item: dict[str, Any]) -> str:
    """买家下单原文，仅作 line1 展示，不参与尺寸解析。"""
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


def _map_row_as_product(km_row: dict[str, Any]) -> dict[str, Any]:
    l, w, h = kms.production_dims_from_map(km_row)
    return {
        "outer_id": km_row.get("outer_id") or "",
        "length": l,
        "width": w,
        "height": h,
        "material": (km_row.get("material") or "").strip(),
        "material_hint": (km_row.get("spec_alias") or "").strip(),
        "product_type": (km_row.get("product_type") or "").strip(),
        "dim_kind": (km_row.get("dim_kind") or "outer").strip() or "outer",
        "source": "km_map_cache",
    }


def resolve_authoritative_product(
    item: dict[str, Any],
    *,
    km_index: dict[str, dict] | None = None,
    fetch_if_missing: bool = False,
) -> dict[str, Any] | None:
    """
    权威生产尺寸（优先级）：
    1. 快麦订单子单 x/y/z
    2. erp.item.single.sku.get
    3. 本地 km_sku_map 缓存（Excel 导入的兜底，非文本解析）
    """
    product = km_api.km_resolve_item_product_dims(
        item, fetch_if_missing=fetch_if_missing
    )
    if product and product.get("length") and product.get("width"):
        return product

    code = item_merchant_code(item)
    if code and km_index is not None:
        row = kms.lookup_outer_id(code, km_index)
        if row and kms.map_has_production_dims(row):
            return _map_row_as_product(row)
    elif code:
        row = kms.lookup_outer_id(code)
        if row and kms.map_has_production_dims(row):
            return _map_row_as_product(row)
    return None


def resolve_line_context(
    item: dict[str, Any],
    *,
    km_index: dict[str, dict] | None = None,
    material_mapping: list[dict] | None = None,
    fetch_if_missing: bool = False,
) -> dict[str, Any]:
    del material_mapping
    sku = item_merchant_code(item)
    order_raw = item_raw_attrs(item)
    km_row = kms.lookup_outer_id(sku, km_index) if sku else None
    product = resolve_authoritative_product(
        item, km_index=km_index, fetch_if_missing=fetch_if_missing
    )

    if product:
        source = product.get("source") or "km_product"
    elif sku:
        source = "km_dims_missing"
    else:
        source = "order_no_sku"

    return {
        "raw_attrs": order_raw,
        "order_spec_raw": order_raw,
        "sku": sku,
        "km_row": km_row,
        "km_product": product,
        "attrs_source": source,
    }


def _apply_product_dims_to_spec(
    ps: dict[str, Any],
    product: dict[str, Any],
    *,
    order_spec_raw: str = "",
    material_mapping: list[dict] | None = None,
) -> dict[str, Any]:
    import production_spec as pspec

    out = dict(ps)
    line1 = (order_spec_raw or ps.get("line1") or ps.get("platform_spec_raw") or "").strip()
    if line1:
        out["line1"] = line1
        out["platform_spec_raw"] = line1

    l = float(product["length"])
    w = float(product["width"])
    h = float(product.get("height") or 0)

    kind = (product.get("dim_kind") or "outer").strip().lower()
    if kind == "inner":
        diam_label = "内径"
    elif kind == "outer":
        diam_label = "外径"
    else:
        diam_label = out.get("diameter_type") or ""

    mat = (product.get("material") or "").strip()
    hint = (product.get("material_hint") or "").strip()
    if not mat and hint:
        mat = pspec.match_production_material(hint, material_mapping) or ""
    if not mat:
        mat = out.get("material") or ""

    color = out.get("color") or ""
    if hint and not color:
        color = pspec._parse_color(hint, mat) or color

    size = pspec.format_size_compact({"l": l, "w": w, "h": h or 0})
    qty_label = out.get("qty_label") or ""
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
            "km_map_override": True,
            "dims_source": product.get("source") or "km_product",
            "km_dims_missing": False,
        }
    )
    return out


def enrich_production_spec(
    ps: dict[str, Any],
    km_row: dict[str, Any] | None,
    *,
    material_mapping: list[dict] | None = None,
    order_spec_raw: str = "",
    km_product: dict[str, Any] | None = None,
    sku: str = "",
) -> dict[str, Any]:
    """
    生产规格：仅用快麦商品档案/映射表结构化尺寸。
    有商家编码时 **禁止** 从买家规格文本解析长宽高。
    """
    if km_product and km_product.get("length") and km_product.get("width"):
        return _apply_product_dims_to_spec(
            ps,
            km_product,
            order_spec_raw=order_spec_raw,
            material_mapping=material_mapping,
        )

    if km_row and kms.map_has_production_dims(km_row):
        return _apply_product_dims_to_spec(
            ps,
            _map_row_as_product(km_row),
            order_spec_raw=order_spec_raw,
            material_mapping=material_mapping,
        )

    out = dict(ps)
    line1 = (order_spec_raw or ps.get("line1") or "").strip()
    if line1:
        out["line1"] = line1
        out["platform_spec_raw"] = line1

    if (sku or "").strip():
        out["dimensions_ok"] = False
        out["dimensions_missing"] = ["长", "宽", "高"]
        out["km_dims_missing"] = True
        out["length"] = None
        out["width"] = None
        out["height"] = None
        return out

    return ps


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
