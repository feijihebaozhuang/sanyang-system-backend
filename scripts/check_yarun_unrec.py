# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('亚润', na=False)
df2 = df[mask]

print('=== 阿里亚润剩余 %d条 ===\n' % len(df2))
for _, row in df2.iterrows():
    print('  %s | 规格ID: %s' % (row['规格名称'], row['平台规格id']))
