# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('三羊', na=False)
df2 = df[mask]
print('=== 阿里三羊剩余 %d条 ===\n' % len(df2))
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if s not in seen:
        seen.add(s)
        print('  %s' % s)
        if len(seen) >= 30:
            break
