# -*- coding: utf-8 -*-
"""测试规格解析 + 采样平台商品看解析效果"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from bind_match import parse_spec_name, build_km_code

# 测试用例
tests = [
    '宽【10cm】高【8cm】内径;【100个】长【38cm】',
    '宽【10cm】高【8cm】;【100个】长【38cm】',
    '长19CM；宽19CM；高10CM',
    '长19CM；宽19CM；高10CM;【200个】',
    '宽【25cm】高【15cm】;【150个】长【35cm】内径',
    '宽:10cm 高:8cm 长:38cm',
    '长30cm 宽20cm 高15cm 内径',
    '定制链接',
    '定做 珍珠棉 包装',
    '宽【15cm】高【10cm】外径;【50个】长【20cm】',
]

print("规格解析测试:")
for t in tests:
    parsed = parse_spec_name(t)
    if parsed:
        if parsed.get('custom'):
            print(f"  [{t[:40]}...] → 定制")
        else:
            cands = build_km_code(parsed)
            print(f"  [{t[:40]}...] → 长={parsed.get('长')},宽={parsed.get('宽')},高={parsed.get('高')},"
                  f"内外径={parsed.get('内外径')},材料={parsed.get('材料')} → {cands}")
    else:
        print(f"  [{t[:40]}...] → 解析失败")
