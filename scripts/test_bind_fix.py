#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试修复后的 bind_match_v4 的 parse_spec_v4"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 直接用 import
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location(
    "bind_match_v4_mod", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "bind_match_v4.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

test_cases = [
    # === 第1组 ===
    ("（宽）135 mm 外径;【100个】 长度 135 mm;105 mm 双面白", "[两组] 宽135外径 + 105双面白"),
    
    # === 第2组 ===
    ("13.5 13.5 10.5   12 13 10  内径 白色", "[两组] 13.5x13.5x10.5 + 12x13x10 内径白"),
    
    # === 第3组 ===
    ("进口优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】", "100x100x100mm → 10x10x10cm 内径特硬"),
    ("10 10 10   内径  特硬", "10x10x10 内径特硬"),
    
    # === 第4组 ===
    ("【双面白色】内径;【36x36 】;10 cm高度（单个价）", "36x36x10cm 内径白色"),
    ("36 36 10  内径 白色", "36x36x10 内径白色"),
    
    # === 第5组 ===
    ("【双面白色】外径;【7x7】;10 cm高度（单个价）", "7x7x10cm 外径白色"),
    ("7 7 10  外径  白色", "7x7x10 外径白色"),
    
    # === 第6组 ===
    ("【台湾纸】外径;【38x38】;5 cm高度（单个价）", "38x38x5cm 外径超硬"),
    ("38 38  5   外径  超硬", "38x38x5 外径超硬"),
]

print("=" * 80)
print("修复后 bind_match_v4.parse_spec_v4 测试")
print("=" * 80)

ok = 0
fail = 0
for text, desc in test_cases:
    result = mod.parse_spec_v4(text)
    if result is None:
        print(f"❌ {desc}")
        print(f"   原文: {text}")
        print(f"   结果: None (平卡/解析失败)")
        fail += 1
    elif result.get('custom'):
        print(f"⚠️  {desc}")
        print(f"   原文: {text}")
        print(f"   结果: 定制 (reason={result['reason']})")
        fail += 1
    else:
        print(f"✅ {desc}")
        print(f"   原文: {text}")
        print(f"   尺寸: 长={result['长']}, 宽={result['宽']}, 高={result['高']}")
        print(f"   内外径: {result['dk']}, 材料: {result['mat']}")
        ok += 1

print(f"\n{'='*60}")
print(f"总计: {ok} ✅, {fail} ❌")
