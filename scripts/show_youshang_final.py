# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()

# 仔细看剩下的高cm+长宽类（含纸箱的）
print('=== 高cm+长宽(LxW cm【长宽】;Hcm 高【五层纸箱】数量) 样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if 'cm【长宽】' in s and '高【' not in s and '高' in s:
        if s not in seen:
            seen.add(s)
            print(f'  {s}')
            if len(seen) >= 5: break

print('\n=== ⑤纸箱cm(高Hcm;长宽【L*W】) 各种变体 ===')
cats = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '高' in s and '长宽【' in s:
        if '层' in s: cats['有层'] += 1
        else: cats['无层'] += 1

print(f'  有层: {cats["有层"]}, 无层: {cats["无层"]}')

print('\n=== 无层样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '高' in s and '长宽【' in s and '层' not in s:
        if s not in seen:
            seen.add(s)
            print(f'  {s}')
            if len(seen) >= 5: break

print('\n=== ②内径mm(剩余)样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【内径尺寸】' in s:
        if s not in seen:
            seen.add(s)
            print(f'  {s}')
            if len(seen) >= 8: break

print('\n=== ③内径直接(剩余)样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【内径】' in s:
        if s not in seen:
            seen.add(s)
            print(f'  {s}')
            if len(seen) >= 5: break

print('\n=== ④外尺寸(剩余)样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if ('外尺寸' in s or '外径' in s) and '【长宽】' not in s:
        if s not in seen:
            seen.add(s)
            print(f'  {s}')
            if len(seen) >= 5: break
