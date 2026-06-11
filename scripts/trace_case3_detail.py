#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追踪用例3 高度 100mm 为什么变成 1.0"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from production_spec import (
    _parse_dimensions,
    _extract_lwh_triple_early,
    _apply_merged_dimension_tags,
    _normalize_parsed_dims_units,
    _val_to_cm,
    _apply_mm_size_heuristic,
)
import re

text = "进口优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】"
print(f"原文: {text}")
print()

# === 完整模拟 _parse_dimensions 中 case3 的流程 ===
dims: dict = {}
dims.update(_extract_lwh_triple_early(text))
print(f"1. _extract_lwh_triple_early → {dims}")

_apply_merged_dimension_tags(dims, text)
print(f"2. _apply_merged_dimension_tags → {dims}")

# === 长宽方括号解析 ===
_LW_IN_BRACKET_RE = re.compile(
    r"长\s*x?\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX\*]\s*(\d+(?:\.\d+)?)\s*(cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
m_lw_in = _LW_IN_BRACKET_RE.search(text)
if m_lw_in:
    u = m_lw_in.group(3) if m_lw_in.lastindex and m_lw_in.lastindex >= 3 else None
    dims.setdefault("l", _val_to_cm(float(m_lw_in.group(1)), u))
    dims.setdefault("w", _val_to_cm(float(m_lw_in.group(2)), u))
    print(f"3. LW_IN_BRACKET: l={m_lw_in.group(1)}, w={m_lw_in.group(2)}, unit={u!r}")
    print(f"   设置后 l={dims['l']}, w={dims['w']}")
print(f"   当前 dims: {dims}")
print()

# === 高度解析 ===
_HEIGHT_BRACKET_RE = re.compile(
    r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)"
    r"[^】]*】",
    re.I,
)
for i, hm in enumerate([
    _HEIGHT_BRACKET_RE.search(text),
    re.search(
        r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?[^】]*】",
        text,
        re.I,
    ),
    re.compile(
        r"【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*高\s*】",
        re.I,
    ).search(text),
    re.search(
        r"(\d+(?:\.\d+)?)\s*(?:mm|MM|毫米)\s*【\s*高\s*】",
        text,
        re.I,
    ),
    re.search(
        r"(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米)\s*高(?!\s*个)",
        text,
        re.I,
    ),
]):
    if hm:
        g0 = hm.group(0) or ""
        u = "mm" if re.search(r"mm|毫米", g0, re.I) else None
        if not u and re.search(r"cm|厘米", g0, re.I):
            u = "cm"
        dims["h"] = _val_to_cm(float(hm.group(1)), u)
        print(f"4.{i} 高度匹配: {hm.groups()}, group(0)={g0!r}")
        print(f"   设置 h={dims['h']} (raw={hm.group(1)}, unit={u!r})")
        break
else:
    print("4. 所有高度模式都不匹配!")

print(f"\n   高度解析后 dims: {dims}")
print()

# === 再试一个关键点：高度是否在 _normalize_parsed_dims_units 中被覆盖 ===
print("5. 调用 _normalize_parsed_dims_units...")
dims_norm = _normalize_parsed_dims_units(dict(dims), text)
print(f"   _normalize_parsed_dims_units 结果: {dims_norm}")
print()

# === 直接调用完整 _parse_dimensions ===
dims_final = _parse_dimensions(text)
print(f"6. _parse_dimensions 最终结果: {dims_final}")
