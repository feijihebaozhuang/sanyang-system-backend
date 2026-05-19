# -*- coding: utf-8 -*-
"""报价纸长/纸度（英寸，与 app.py calc_* 一致，供生产算料复用）。"""
from __future__ import annotations

import math
from typing import Any


def ceil_to_half(val: float) -> float:
    """向上取整到 0.5（与 app.py 一致）。"""
    return math.ceil(val * 2) / 2


def ceil_to_spec(val: float, spec_list: list, multiply_limit: int = 3) -> float:
    min_spec = min(spec_list)
    if val >= min_spec:
        for s in spec_list:
            if val <= s:
                return s
        return max(spec_list)
    for mult in range(2, multiply_limit + 1):
        multiplied = val * mult
        ceil_odd = math.ceil(multiplied)
        if ceil_odd % 2 == 0:
            ceil_odd += 1
        if ceil_odd >= min_spec:
            for s in spec_list:
                if ceil_odd <= s:
                    return s / mult
            return max(spec_list) / mult
    return min_spec / multiply_limit


def calc_paper_inches(
    product_type: str,
    length: float,
    width: float,
    height: float,
    *,
    quote_data: dict | None = None,
    is_buckle: bool = False,
    material_key: str = "d6d",
) -> dict[str, Any]:
    """
    复用 app.py 各产品公式，输出已取整的 paper_l_inch / paper_w_inch。
    product_type: 飞机盒|带扣|扣底盒|双插盒|纸箱
    """
    qd = quote_data or {}
    pt = (product_type or "飞机盒").strip()
    l, w, h = float(length), float(width), float(height)
    buckle = is_buckle or pt in ("带扣", "daikou", "带扣飞机盒")

    if pt in ("扣底盒", "koudi"):
        paper_l_cm = l * 2 + w * 2 + 3
        paper_w_cm = w + h + w / 2 + 3 + 2
        paper_l_inch = ceil_to_half(paper_l_cm / 2.54)
        paper_w_inch = ceil_to_half(paper_w_cm / 2.54)
    elif pt in ("双插盒", "shuangcha"):
        paper_l_cm = l * 2 + w * 2 + 3
        paper_w_cm = w * 2 + 6 + h
        paper_l_inch = ceil_to_half(paper_l_cm / 2.54)
        paper_w_inch = ceil_to_half(paper_w_cm / 2.54)
    elif pt in ("纸箱", "carton"):
        specs = qd.get("cardboard_specs", {})
        paper_lengths = specs.get(
            "danbu_paper_lengths",
            list(range(29, 91)),
        )
        paper_widths = specs.get(
            "danbu_paper_widths",
            [29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49],
        )
        max_danbu_cm = float(specs.get("max_danbu_length_cm", 230))
        danbu_paper_l_cm = (l + w) * 2 + 3.5
        if danbu_paper_l_cm > max_danbu_cm:
            paper_l_cm = ((l + w) + 3.5) * 2
        else:
            paper_l_cm = danbu_paper_l_cm
        paper_w_cm = w + h + 0.6
        paper_l_inch = ceil_to_spec(paper_l_cm / 2.54, paper_lengths)
        paper_w_inch = ceil_to_spec(paper_w_cm / 2.54, paper_widths)
    else:
        if buckle:
            paper_l_cm = 3 * h + 2 * w + 3
        else:
            paper_l_cm = 3 * h + 2 * w
        paper_w_cm = l + 4 * h + 4
        paper_l_inch = ceil_to_half(paper_l_cm / 2.54)
        paper_w_inch = ceil_to_half(paper_w_cm / 2.54)

    return {
        "product_type": pt,
        "paper_l_inch": round(float(paper_l_inch), 2),
        "paper_w_inch": round(float(paper_w_inch), 2),
        "paper_l_cm": round(paper_l_cm, 2),
        "paper_w_cm": round(paper_w_cm, 2),
        "finished_l": l,
        "finished_w": w,
        "finished_h": h,
        "material_key": material_key,
    }


def expand_dimensions(
    product_type: str,
    length: float,
    width: float,
    height: float,
    *,
    quote_data: dict | None = None,
    is_buckle: bool = False,
) -> dict[str, Any]:
    """兼容旧调用：返回英寸为主，spread_*_cm 为英寸×2.54 仅供参考。"""
    r = calc_paper_inches(
        product_type, length, width, height, quote_data=quote_data, is_buckle=is_buckle
    )
    return {
        **r,
        "spread_l_cm": round(r["paper_l_inch"] * 2.54, 2),
        "spread_w_cm": round(r["paper_w_inch"] * 2.54, 2),
    }
