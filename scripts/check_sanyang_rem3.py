# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('三羊', na=False)
df2 = df[mask]

seen = set()
count = 0
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '外尺寸' in s and '外尺寸白色' not in s:
        if s not in seen:
            seen.add(s)
            print('  %s' % s)
            count += 1
            if count >= 15:
                break

print('\n=== 其他(不是外尺寸的) ===')
seen2 = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '外尺寸' not in s:
        if s not in seen2:
            seen2.add(s)
            print('  %s' % s)
            if len(seen2) >= 10:
                break
