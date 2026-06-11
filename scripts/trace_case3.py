#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""详细追踪用例3的解析过程"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from production_spec import (
    _parse_dimensions,
    _extract_lwh_triple_early,
    _apply_merged_dimension_tags,
    _normalize_parsed_dims_units,
    _val_to_cm,
)
import re

text = "进口优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】"
print(f"原文: {text}")
print()

# 追踪 _extract_lwh_triple_early
dims = _extract_lwh_triple_early(text)
print(f"1. _extract_lwh_triple_early: {dims}")

# 模拟实际解析流程
dims2 = {}
dims2.update(_extract_lwh_triple_early(text))

# 长宽标签
_LW_IN_BRACKET_RE = re.compile(
    r"长\s*x?\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX\*]\s*(\d+(?:\.\d+)?)\s*(cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
m_lw = _LW_IN_BRACKET_RE.search(text)
if m_lw:
    print(f"2. LW_IN_BRACKET: groups={m_lw.groups()}")
    u = m_lw.group(3) if m_lw.lastindex and m_lw.lastindex >= 3 else None
    dims2["l"] = _val_to_cm(float(m_lw.group(1)), u)
    dims2["w"] = _val_to_cm(float(m_lw.group(2)), u)
    print(f"   设置 l={dims2['l']}, w={dims2['w']} (unit={u})")

print(f"\n   当前 dims: {dims2}")

# 高度解析
_HEIGHT_BRACKET_RE = re.compile(
    r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)"
    r"[^】]*】",
    re.I,
)

hm = _HEIGHT_BRACKET_RE.search(text)
print(f"\n3. HEIGHT_BRACKET: {hm}")
if hm:
    print(f"   groups={hm.groups()}, group(0)={hm.group(0)}")
else:
    # 试试其他高度模式
    pats = [
        (r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?[^】]*】", "标准"),
        (r"(?:高度|高)\s*【?\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*】?", "标签外"),
        (r"(\d+(?:\.\d+)?)\s*(?:mm|MM|毫米)\s*【\s*高\s*】", "数字前"),
        (r"【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*高\s*】", "高在数字后"),
        (r"(\d+(?:\.\d+)?)\s*(?:mm|MM|毫米)\s*高(?!\s*个)", "mm高"),
    ]
    for pat, name in pats:
        m = re.search(pat, text, re.I)
        if m:
            print(f"   匹配了 {name}: {m.groups()}, group(0)={m.group(0)}")
    
print("\n\n=== 现在追踪 _normalize_parsed_dims_units ===")
# 先模拟 _parse_dimensions 的高度的代码
dims3 = dict(dims2)
for hm in (
    re.compile(r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?[^】]*】", re.I).search(text),
    None,  # 跳过第二个
    None,
    None,
    None,
    None,
):
    if hm:
        g0 = hm.group(0) or ""
        u = "mm" if re.search(r"mm|毫米", g0, re.I) else None
        if not u and re.search(r"cm|厘米", g0, re.I):
            u = "cm"
        dims3["h"] = _val_to_cm(float(hm.group(1)), u)
        print(f"设置 h={dims3['h']} (raw={hm.group(1)}, unit={u} from group(0)={g0})")
        break

# 然后再看看 _apply_mm_size_heuristic
from production_spec import _apply_mm_size_heuristic

print(f"\n调用 _apply_mm_size_heuristic 前: {dims3}")
final_dims = _apply_mm_size_heuristic(dims3, text)
print(f"调用 _apply_mm_size_heuristic 后: {final_dims}")
