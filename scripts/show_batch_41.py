# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\OK文件\换绑文件_第41批.xlsx'
df = pd.read_excel(f, skiprows=1)
print(f'第41批: {len(df)} 条')
for _, r in df.iterrows():
    shop = r['店铺名称']
    code = r['商品编码']
    print(f'  {shop} | {code}')
