# -*- coding: utf-8 -*-
"""调试正则"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

tests = [
    ('模式B', r'进口优质.*?(内径|外经|外径)\s*;\s*长x宽[【】\s]*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*mm?[】]*\s*;\s*(\d+\.?\d*)\s*mm?',
     '进口优质特硬E瓦-内径;长x宽【100x100】mm;100mm【高】'),
    ('模式C', r'【([^】]*)】\s*(内径|外径)\s*;\s*[【】\s]*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)[】]*\s*;\s*(\d+\.?\d*)\s*cm?\s*高度',
     '【双面白色】内径;【36x36 】;10 cm高度（单个价）'),
]

for name, pat, s in tests:
    m = re.search(pat, s)
    print(f'{name}: {m is not None}')
    if m:
        print(f'  groups: {m.groups()}')
    # 逐个字符检查
    print(f'  string hex: {" ".join(f"U+{ord(c):04X}" for c in s[:30])}')
