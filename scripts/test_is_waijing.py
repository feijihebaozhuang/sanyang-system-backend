# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def is_waijing(s):
    if '内径' in s or '内尺寸' in s:
        if '外径' in s or '外尺寸' in s:
            return True
        return False
    return True

tests = [
    "白色【100个】宽度 10 CM;长 11 *宽 ? * 高 6 【所量即所装=内径】",
    "白色【内径】100个;10x10x2 cm",
    "黑色【内尺寸】【100个】;10x10x2 cm",
    "进口牛皮色【内尺寸】;10x10x2 cm",
    "宽度 10 CM 特硬-牛皮色【100个】;长 11 *宽 ? * 高 6 【所量即所装=内径】",
    "宽【10cm】高【8cm】内径;【100个】长【39cm】",  # 明确内径
]

for s in tests:
    result = '外径' if is_waijing(s) else '内径'
    print(f'  {result}: {s[:60]}')
