# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)
mask = df['店铺简称'].str.contains('止合', na=False)
zh = df[mask].copy().reset_index(drop=True)

s = str(zh.iloc[108]['规格名称']).strip()
for i, ch in enumerate(s):
    if ord(ch) > 127:
        print(f'  [{i}]{ch} U+{ord(ch):04X}')
# 看第2个分号前后的字符
print()
for i, ch in enumerate(s):
    if ch in '；;':
        print(f'  [{i}]"{ch}" U+{ord(ch):04X}')
