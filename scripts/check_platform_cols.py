# -*- coding: utf-8 -*-
import sys, os, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pf = r'd:\Desktop\平台商品.xlsx'

# 看看表头行
df0 = pd.read_excel(pf, sheet_name='报表1', header=None, dtype=str)
print("前5行表头:")
for i in range(5):
    vals = [str(v)[:20] for v in df0.iloc[i].values]
    print(f"  第{i}行: {vals}")

# 用header=2读
print("\n\nheader=2 列名:")
df = pd.read_excel(pf, sheet_name='报表1', header=2, dtype=str)
print(list(df.columns))
print(f"\n前3行数据:")
for i in range(3):
    vals = [str(v)[:25] for v in df.iloc[i].values]
    print(f"  {vals}")
