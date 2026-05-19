# -*- coding: utf-8 -*-
"""报价展开尺寸计算（供生产算料复用，不含报价金额）。"""
from __future__ import annotations

import math
from typing import Any


def ceil_to_half(val: float) -> float:
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


def expand_dimensions(
    product_type: str,
    length: float,
    width: float,
    height: float,
    *,
    quote_data: dict | None = None,
    is_buckle: bool = False,
) -> dict[str, Any]:
    """
    返回展开尺寸（厘米）：spread_l_cm=纸长方向, spread_w_cm=纸度方向。
    product_type: 飞机盒|带扣|扣底盒|双插盒|纸箱
    """
    qd = quote_data or {}
    pt = (product_type or "飞机盒").strip()
    l, w, h = float(length), float(width), float(height)

    if pt in ("扣底盒", "koudi"):
        paper_l_cm = l * 2 + w * 2 + 3
        paper_w_cm = w + h + w / 2 + 3 + 2
    elif pt in ("双插盒", "shuangcha"):
        paper_l_cm = l * 2 + w * 2 + 2
        paper_w_cm = h + w + 2
    elif pt in ("纸箱", "carton"):
        specs = qd.get("cardboard_specs", {})
        paper_lengths = specs.get(
            "danbu_paper_lengths",
            list(range(29, 91)),
        )
        paper_widths = specs.get("danbu_paper_widths", [29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 49])
        max_danbu_cm = float(specs.get("max_danbu_length_cm", 230))
        danbu_paper_l_cm = (l + w) * 2 + 3.5
        paper_l_cm = ((l + w) + 3.5) * 2 if danbu_paper_l_cm > max_danbu_cm else danbu_paper_l_cm
        paper_w_cm = w + h + 0.6
        paper_l_cm = float(
            ceil_to_spec(paper_l_cm / 2.54, paper_lengths) * 2.54
        )
        paper_w_cm = float(ceil_to_spec(paper_w_cm / 2.54, paper_widths) * 2.54)
    else:
        buckle = is_buckle or pt in ("带扣", "daikou", "带扣飞机盒")
        if buckle:
            paper_l_cm = 3 * h + 2 * w + 3
        else:
            paper_l_cm = 3 * h + 2 * w
        paper_w_cm = l + 4 * h + 4
        paper_l_cm = ceil_to_half(paper_l_cm)
        paper_w_cm = ceil_to_half(paper_w_cm)

    return {
        "product_type": pt,
        "spread_l_cm": round(paper_l_cm, 2),
        "spread_w_cm": round(paper_w_cm, 2),
        "finished_l": l,
        "finished_w": w,
        "finished_h": h,
    }
