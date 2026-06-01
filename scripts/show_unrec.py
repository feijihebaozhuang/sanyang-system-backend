# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)
mask = df['标记'].str.contains('未识别', na=False)
unrec = df[mask]
print(f'未识别共 {len(unrec)} 条')
for _, r in unrec.iterrows():
    shop = r['店铺简称']
    spec = r['规格名称']
    print(f'  [{shop}] {spec}')
