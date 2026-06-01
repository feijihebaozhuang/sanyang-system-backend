# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)
mask = df['\u5e97\u94fa\u7b80\u79f0'].str.contains('\u6b62\u5408', na=False)
zh = df[mask].copy().reset_index(drop=True)
specs = zh['\u89c4\u683c\u540d\u79f0'].dropna().astype(str).str.strip()

print(f'\u5929\u732b\u6b62\u5408\u5728\u65e0\u5339\u914d\u4e2d: {len(zh)} \u6761\n')
print('=== \u5168\u90e8\u89c4\u683c ===')
for i, s in enumerate(specs):
    print(f'  {i+1}. {s}')
