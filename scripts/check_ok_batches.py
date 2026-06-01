# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

# 第41批
f = r'D:\Desktop\换绑输出\OK文件\换绑文件_第41批.xlsx'
df = pd.read_excel(f, skiprows=1)
print(f'第41批: {len(df)} 条')
print('商品编码:')
for _, r in df.iterrows():
    code = r['商品编码']
    print(f'  {code}')
    parts = code.split('-')
    if len(parts) == 3:
        dims = [float(x) for x in parts[0].split('*')]
        dk = parts[1]
        mat = parts[2]

# 再看第40批
f40 = r'D:\Desktop\换绑输出\OK文件\换绑文件_第40批.xlsx'
if os.path.exists(f40):
    df40 = pd.read_excel(f40, skiprows=1)
    print(f'\n第40批: {len(df40)} 条')
    for _, r in df40.iterrows():
        print(f'  {r["商品编码"]}')
