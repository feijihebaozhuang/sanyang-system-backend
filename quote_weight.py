# -*- coding: utf-8 -*-
"""单件重量估算：与报价/算料同一套展开面积×克重公式（quote_data.json）。"""
from __future__ import annotations

import json
import math
import os
from typing import Any

import quote_calc_core as qcc

_SQ_IN_TO_M2 = 0.00064516
_QUOTE_FILE = os.path.join(os.path.dirname(__file__), "quote_data.json")


def load_quote_data() -> dict[str, Any]:
    try:
        from quote_material_defaults import enrich_quote_data

        with open(_QUOTE_FILE, "r", encoding="utf-8") as f:
            return enrich_quote_data(json.load(f))
    except Exception:
        return {}


def _material_group(product_type: str) -> str:
    pt = (product_type or "").strip()
    if pt in ("koudi", "shuangcha"):
        return "koudi"
    if pt in ("qita", "carton"):
        return "carton"
    if pt == "pe":
        return "pe"
    return "airbox"


def _gram_weight(quote_data: dict, material_key: str, product_type: str) -> float:
    group = _material_group(product_type)
    mats = (quote_data.get("materials") or {}).get(group, {}).get("materials") or {}
    info = mats.get(material_key) or {}
    defaults = {"carton": 380, "koudi": 450, "airbox": 450, "pe": 0}
    return float(info.get("gram_weight") or defaults.get(group, 450))


def infer_material_key(text: str, quote_data: dict | None = None) -> str:
    import material_calc as mc
    import production_spec as pspec

    qd = quote_data or load_quote_data()
    mat_map = qd.get("material_mapping") or []
    label = pspec.match_production_material(text or "", mat_map)
    return mc.resolve_material_key(label or text or "", qd)


def infer_quote_product_type(
    text: str,
    *,
    length: float = 0,
    width: float = 0,
) -> str:
    import production_spec as pspec

    blob = (text or "").strip()
    if "珍珠棉" in blob or re_is_pe(blob):
        return "pe"
    cat = pspec.infer_product_category(blob)
    if cat == "纸箱":
        return "qita"
    if cat == "扣底盒":
        return "koudi"
    if "双插" in blob:
        return "shuangcha"
    if "带扣" in blob or cat == "带扣":
        return "daikou"
    l, w = float(length or 0), float(width or 0)
    if l > 0 and w > 0 and abs(l - w) < 0.01:
        return "zhengsquare"
    return "juxing"


def re_is_pe(blob: str) -> bool:
    b = (blob or "").upper()
    return b.startswith("PE") or "EPE" in b


def is_inner_spec(text: str) -> bool:
    t = (text or "").strip()
    return "内径" in t and "外径" not in t


def outer_dims_for_quote(
    product_type: str,
    length: float,
    width: float,
    height: float,
    *,
    text: str = "",
) -> tuple[float, float, float, str]:
    """内径正方形飞机盒：与报价 API 一致 +1.5/+0.5/+0.5。"""
    l, w, h = float(length), float(width), float(height or 0)
    pt = (product_type or "").strip()
    inner = is_inner_spec(text) or pt.endswith("-inner")
    if inner and pt.replace("-inner", "") in ("zhengsquare", ""):
        if abs(l - w) < 0.01 or pt.startswith("zhengsquare"):
            return l + 1.5, w + 0.5, h + 0.5, "内径→外径"
    return l, w, h, "外径" if not inner else "尺寸"


def estimate_unit_weight(
    length: float,
    width: float,
    height: float,
    *,
    text: str = "",
    product_type: str = "",
    material_key: str = "",
    quote_data: dict | None = None,
) -> dict[str, Any]:
    """
    返回单件重量（克/千克）及推断信息。
    长宽高单位：cm（纸类）；珍珠棉为 mm（与报价页一致）。
    """
    qd = quote_data or load_quote_data()
    l, w, h = float(length or 0), float(width or 0), float(height or 0)
    if not (l > 0 and w > 0 and h > 0):
        return {"ok": False, "error": "缺少长宽高"}

    ptype = (product_type or "").strip() or infer_quote_product_type(text, length=l, width=w)
    mat_key = (material_key or "").strip() or infer_material_key(text, qd)

    if ptype == "pe":
        # 报价页输入 mm；若数值像 cm（<=120）则×10 转 mm
        lm, wm, hm = l, w, h
        if max(lm, wm, hm) <= 120:
            lm, wm, hm = l * 10, w * 10, h * 10
        hm = math.ceil(hm / 0.5) * 0.5 or 0.5
        l_cm, w_cm, h_cm = lm / 10, wm / 10, hm / 10
        weight_kg = l_cm * w_cm * h_cm / 5000
        weight_g = weight_kg * 1000
        return {
            "ok": True,
            "product_type": ptype,
            "material_key": mat_key,
            "weight_per_unit_g": round(weight_g, 2),
            "weight_per_unit_kg": round(weight_kg, 4),
            "dim_note": "珍珠棉(mm→泡重)",
        }

    ol, ow, oh, dim_note = outer_dims_for_quote(ptype, l, w, h, text=text)
    is_buckle = ptype == "daikou"
    calc_pt = {
        "koudi": "扣底盒",
        "shuangcha": "双插盒",
        "qita": "纸箱",
        "daikou": "飞机盒",
    }.get(ptype, "飞机盒")

    inches = qcc.calc_paper_inches(
        calc_pt,
        ol,
        ow,
        oh,
        quote_data=qd,
        is_buckle=is_buckle,
        material_key=mat_key,
    )
    pl_in = float(inches["paper_l_inch"])
    pw_in = float(inches["paper_w_inch"])
    gram = _gram_weight(qd, mat_key, ptype)
    area_m2 = pl_in * pw_in * _SQ_IN_TO_M2
    weight_g = area_m2 * gram
    weight_kg = weight_g / 1000

    return {
        "ok": True,
        "product_type": ptype,
        "material_key": mat_key,
        "paper_l_inch": pl_in,
        "paper_w_inch": pw_in,
        "gram_weight": gram,
        "weight_per_unit_g": round(weight_g, 2),
        "weight_per_unit_kg": round(weight_kg, 4),
        "dim_note": dim_note,
        "outer_l": ol,
        "outer_w": ow,
        "outer_h": oh,
    }
