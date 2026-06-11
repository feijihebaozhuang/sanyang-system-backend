# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
df = pd.read_excel(source, dtype=str)
print(f'总行数: {len(df)}')
print(f'列名: {list(df.columns)}')
print()
print(df.head(10).to_string(index=False))
