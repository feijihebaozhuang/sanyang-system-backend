# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('大鱼', na=False)
df2 = df[mask]

print('=== 阿里大鱼剩余 %d条 ===\n' % len(df2))
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if s not in seen:
        seen.add(s)
        print('  %s' % s)
