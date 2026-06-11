# -*- coding: utf-8 -*-
"""
从平台商品.xlsx中排除已找出的小数商品(17276条)，剩下的全部输出到桌面
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(f, header=1, dtype=str)
total = len(df)

# 已找出的小数商品 = 有小数非全.5 + 三项全.5
dot_file = r'D:\Desktop\长宽高含小数商品.xlsx'
df_dot = pd.read_excel(dot_file, skiprows=1, dtype=str)
dot_ids = set(df_dot['平台商品id'].dropna().astype(str).str.strip())

# 排除小数商品
mask = ~df['平台商品id'].astype(str).isin(dot_ids)
remaining = df[mask].copy()

print(f'总共: {total}')
print(f'小数(已排除): {len(df_dot)}')
print(f'剩余(整数为主): {len(remaining)}')

# 输出
out = r'D:\Desktop\整数商品.xlsx'
remaining.to_excel(out, index=False, columns=['店铺名称', '平台商品id', '平台规格名称', '平台规格id'])

import openpyxl
wb = openpyxl.load_workbook(out)
ws = wb.active
ws.insert_rows(1)
ws.cell(1, 2).value = '整数商品（已排除小数项）'
ws.column_dimensions['C'].width = 60
wb.save(out)

print(f'\n✅ 已输出到: {out}')
print(f'共 {len(remaining)} 条')
