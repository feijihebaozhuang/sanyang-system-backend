#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确定位 高度 100mm->1cm 的 bug - 修正版"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from production_spec import _val_to_cm, _apply_mm_size_heuristic
import re

text = "进口优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】"

# 在 _parse_dimensions 的 for 循环中，各高度模式依次尝试：
_HEIGHT_BRACKET_RE = re.compile(
    r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)"
    r"[^】]*】",
    re.I,
)

patterns = [
    ("_HEIGHT_BRACKET_RE", _HEIGHT_BRACKET_RE),
    ("宽放_H", re.compile(r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?[^】]*】", re.I)),
    ("_HEIGHT_NUM_FIRST_RE", re.compile(r"【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*高\s*】", re.I)),
    ("mm【高】", re.compile(r"(\d+(?:\.\d+)?)\s*(?:mm|MM|毫米)\s*【\s*高\s*】", re.I)),
    ("cm高", re.compile(r"(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米)\s*高(?!\s*个)", re.I)),
]

for name, pat in patterns:
    m = pat.search(text)
    if m:
        g0 = m.group(0)
        raw_val = float(m.group(1))
        u = "mm" if re.search(r"mm|毫米", g0, re.I) else None
        if not u and re.search(r"cm|厘米", g0, re.I):
            u = "cm"
        print(f"  {name}: group(0)={g0!r}, raw_val={raw_val}, unit={u!r}")
        print(f"  _val_to_cm({raw_val}, {u!r}) = {_val_to_cm(raw_val, u)}")

print()
print("=== 实际 _parse_dimensions 中的循环 ===")
# 模拟实际代码中的 break 逻辑
for hm in (
    _HEIGHT_BRACKET_RE.search(text),
    re.search(
        r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?[^】]*】",
        text, re.I,
    ),
    re.compile(r"【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*高\s*】", re.I).search(text),
    re.search(
        r"(\d+(?:\.\d+)?)\s*(?:mm|MM|毫米)\s*【\s*高\s*】",
        text, re.I,
    ),
    re.search(
        r"(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米)\s*高(?!\s*个)",
        text, re.I,
    ),
):
    if hm:
        g0 = hm.group(0) or ""
        u = "mm" if re.search(r"mm|毫米", g0, re.I) else None
        if not u and re.search(r"cm|厘米", g0, re.I):
            u = "cm"
        val = _val_to_cm(float(hm.group(1)), u)
        print(f"  命中: group(0)={g0!r}, raw={hm.group(1)}, unit={u!r}, h={val}")
        break

print()
print("=== 关键是 lw 解析时带单位的问题 ===")
# 看 LW_IN_BRACKET_RE 因为 mm 在】外面导致 unit=None
_LW_IN_BRACKET_RE = re.compile(
    r"长\s*x?\s*宽\s*【\s*(\d+(?:\.\d+)?)\s*[*×xX\*]\s*(\d+(?:\.\d+)?)\s*(cm|CM|厘米|mm|MM|毫米)?\s*】",
    re.I,
)
m = _LW_IN_BRACKET_RE.search(text)
if m:
    print(f"  LW_IN_BRACKET: groups={m.groups()}")
    print(f"  注意：mm 在】外面, group(3)={m.group(3)!r}")
