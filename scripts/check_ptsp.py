# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\平台商品.xlsx'

# 先看sheet名和列
xl = pd.ExcelFile(f)
print(f'Sheets: {xl.sheet_names}')

df = pd.read_excel(f)
print(f'\n列名: {list(df.columns)}')
print(f'总行: {len(df)}')
print(f'\n前3行:')
print(df.head(3).to_string())
