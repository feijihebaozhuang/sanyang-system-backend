#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规格尺寸解析 + 档案为空兜底（非 pytest，直接 python 运行）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import km_sku_resolve as ksr
import production_spec as pspec


def test_wh_l_pattern() -> None:
    text = "宽高【11*5】黄色；长21 cm"
    dims = pspec.parse_dimensions_cm(text)
    assert dims.get("l") == 21.0, dims
    assert dims.get("w") == 11.0, dims
    assert dims.get("h") == 5.0, dims


def test_enrich_fallback() -> None:
    raw = "宽高【11*5】黄色；长21 cm"
    ps = pspec.build_production_spec(raw, 100)
    out = ksr.enrich_production_spec(
        ps,
        None,
        order_spec_raw=raw,
        km_product=None,
        sku="TEST-SKU-52700",
    )
    assert out.get("dimensions_ok"), out
    assert out.get("length") == 21.0
    assert out.get("width") == 11.0
    assert out.get("height") == 5.0
    assert out.get("km_spec_fallback") is True
    assert out.get("km_dims_missing") is False


def main() -> int:
    test_wh_l_pattern()
    test_enrich_fallback()
    print("ok: spec dims fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
