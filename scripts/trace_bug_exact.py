#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确定位 高度 100mm->1cm 的 bug"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from production_spec import _val_to_cm
import re

text = "进口优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】"
print(f"原文: {text}")

# 看看哪个模式先匹配

# 模式4.0: _HEIGHT_BRACKET_RE
_HEIGHT_BRACKET_RE = re.compile(
    r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)"
    r"[^】]*】",
    re.I,
)
m = _HEIGHT_BRACKET_RE.search(text)
print(f"\n_HEIGHT_BRACKET_RE: {m}")
if m: print(f"  group(0)={m.group(0)!r}, group(1)={m.group(1)}")

# 模式4.1: 放宽版
m = re.search(
    r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?[^】]*】",
    text,
    re.I,
)
print(f"\n宽放版_HEIGHT: {m}")
if m: print(f"  group(0)={m.group(0)!r}, group(1)={m.group(1)}")

# 模式4.2: _HEIGHT_NUM_FIRST_RE — 数字在【内，高在【内
_HEIGHT_NUM_FIRST_RE = re.compile(
    r"【\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?\s*高\s*】",
    re.I,
)
m = _HEIGHT_NUM_FIRST_RE.search(text)
print(f"\n_HEIGHT_NUM_FIRST_RE: {m}")
if m: print(f"  group(0)={m.group(0)!r}, group(1)={m.group(1)}")

# 模式4.3: 数字前 mm【高】
m = re.search(
    r"(\d+(?:\.\d+)?)\s*(?:mm|MM|毫米)\s*【\s*高\s*】",
    text,
    re.I,
)
print(f"\nmm【高】模式: {m}")
if m: print(f"  group(0)={m.group(0)!r}, group(1)={m.group(1)}, group(2)={m.group(2)}")

# 模式4.4: cm高
m = re.search(
    r"(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米)\s*高(?!\s*个)",
    text,
    re.I,
)
print(f"\ncm高模式: {m}")
if m: print(f"  group(0)={m.group(0)!r}, group(1)={m.group(1)}")

print("\n\n=== 现在看 _parse_dimensions 内部实际流程 ===")
# 模拟实际流程中的 for 循环
print("\n在 _parse_dimensions 中的 for hm 循环:")
hm0 = _HEIGHT_BRACKET_RE.search(text)
print(f"hm0=_HEIGHT_BRACKET_RE → {hm0}")

hm1 = re.search(
    r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?[^】]*】",
    text,
    re.I,
)
print(f"hm1=宽放版 → {hm1}")

hm2 = _HEIGHT_NUM_FIRST_RE.search(text)
print(f"hm2=_HEIGHT_NUM_FIRST_RE → {hm2}")

hm3 = re.search(
    r"(\d+(?:\.\d+)?)\s*(?:mm|MM|毫米)\s*【\s*高\s*】",
    text,
    re.I,
)
print(f"hm3=mm【高】 → {hm3}")

hm4 = re.search(
    r"(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米)\s*高(?!\s*个)",
    text,
    re.I,
)
print(f"hm4=cm高 → {hm4}")

# 关键：哪个最先被匹配到？
pat_tests = [
    ("_HEIGHT_BRACKET_RE", _HEIGHT_BRACKET_RE),
    ("宽放_H", re.compile(r"【\s*(?:高度|高)\s*(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米|mm|MM|毫米)?[^】]*】", re.I)),
    ("_HEIGHT_NUM_FIRST_RE", _HEIGHT_NUM_FIRST_RE),
    ("mm【高】", re.compile(r"(\d+(?:\.\d+)?)\s*(?:mm|MM|毫米)\s*【\s*高\s*】", re.I)),
    ("cm高", re.compile(r"(\d+(?:\.\d+)?)\s*(?:cm|CM|厘米)\s*高(?!\s*个)", re.I)),
]

for name, pat in pat_tests:
    m = pat.search(text)
    if m:
        g0 = m.group(0)
        u = "mm" if re.search(r"mm|毫米", g0, re.I) else None
        if not u and re.search(r"cm|厘米", g0, re.I):
            u = "cm"
        print(f"\n  {name}: group(1)={m.group(1)}, unit={u!r}")
        print(f"  _val_to_cm({m.group(1)}, {u!r}) = {_val_to_cm(float(m.group(1)), u)}")

# 再看看 _apply_mm_size_heuristic
print("\n\n=== 看看 _apply_mm_size_heuristic ===")
from production_spec import _apply_mm_size_heuristic

# 假如 h=10 进了 heuristic
print(f"输入 {{'l':100, 'w':100, 'h':10}} → {_apply_mm_size_heuristic({'l':100, 'w':100, 'h':10}, text)}")
# 假如 h=100 进了 heuristic
print(f"输入 {{'l':100, 'w':100, 'h':100}} → {_apply_mm_size_heuristic({'l':100, 'w':100, 'h':100}, text)}")
