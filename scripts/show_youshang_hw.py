# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()

cats = Counter()
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '高' in s and 'cm' in s and '长宽【' in s:
        cats['有【】'] += 1
        if '层' in s: 
            if '5层' in s: cats['5层'] += 1
            elif '3层' in s: cats['3层'] += 1
            elif '五层' in s: cats['五层'] += 1
            elif '三层' in s: cats['三层'] += 1
            else: cats['其他层'] += 1
        else:
            cats['无层'] += 1
        if s not in seen:
            seen.add(s)
            
print('=== 高cm+长宽类别 ===')
for k, v in cats.most_common():
    print(f'  {k}: {v}')

print('\n=== 高cm+长宽(有层) 样本 ===')
count = 0
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '高' in s and 'cm' in s and '长宽【' in s and '层' in s:
        print(f'  {s}')
        count += 1
        if count >= 15: break

print('\n=== 高cm+长宽(无层) 样本 ===')
count = 0
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '高' in s and 'cm' in s and '长宽【' in s and '层' not in s:
        print(f'  {s}')
        count += 1
        if count >= 15: break
