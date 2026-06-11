#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试用户提供的规格文本解析结果"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from production_spec import (
    _parse_dimensions,
    _parse_diameter_type,
    parse_quantity_info,
    match_production_material,
    format_size_compact,
)

# 用户的输入原文
test_cases = [
    # === 第1组：宽135外径，100个，长度135，105双面白 ===
    "（宽）135 mm 外径;【100个】 长度 135 mm;105 mm 双面白",
    
    # === 第2组：13.5 13.5 10.5 || 12 13 10 内径 白色 ===
    "13.5 13.5 10.5   12 13 10  内径 白色",
    
    # === 第3组：优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】 ===
    "进口优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】",
    "10 10 10   内径  特硬",
    
    # === 第4组：双面白色内径 36x36 10cm高 ===
    "【双面白色】内径;【36x36 】;10 cm高度（单个价）",
    "36 36 10  内径 白色",
    
    # === 第5组：双面白色外径 7x7 10cm ===
    "【双面白色】外径;【7x7】;10 cm高度（单个价）",
    "7 7 10  外径  白色",
    
    # === 第6组：台湾纸外径 38x38 5cm ===
    "【台湾纸】外径;【38x38】;5 cm高度（单个价）",
    "38 38  5   外径  超硬",
]

print("=" * 80)
print("三羊包装 - 规格解析测试")
print("=" * 80)

for i, text in enumerate(test_cases):
    print(f"\n{'='*60}")
    print(f"【用例 {i+1}】原文: {text}")
    print(f"{'='*60}")
    
    dims = _parse_dimensions(text)
    diameter = _parse_diameter_type(text)
    qinfo = parse_quantity_info(text, 1)
    
    size_str = format_size_compact(dims)
    
    print(f"  尺寸: l={dims.get('l')}, w={dims.get('w')}, h={dims.get('h')}")
    print(f"  尺寸展示: {size_str or '<空>'}")
    print(f"  内外径: {diameter}")
    print(f"  数量: {qinfo.get('qty_label') or '<无>'}")
    print(f"  数量source: {qinfo.get('qty_source')}")
