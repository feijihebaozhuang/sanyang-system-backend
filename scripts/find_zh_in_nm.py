# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)
print(f'列名: {list(df.columns)}')
print(f'总行: {len(df)}')

# 搜止合
cols = list(df.columns)
for c in cols:
    vals = df[c].dropna().astype(str)
    zh = vals[vals.str.contains('\u6b62\u5408', na=False)]
    if len(zh) > 0:
        print(f'  {c}: \u627e\u5230{len(zh)}\u6761\u6b62\u5408')
        print(f'    前3: {zh.head(3).tolist()}')
