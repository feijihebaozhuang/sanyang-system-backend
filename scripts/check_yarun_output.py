# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

wb = oxl.load_workbook(r'D:\Desktop\换绑_深圳市亚润包装材料有限公司.xlsx')
ws = wb.active

# 采样看不同编码
codes = Counter()
for row in ws.iter_rows(min_row=3, values_only=True):
    codes[str(row[3] or '')] += 1
wb.close()

print(f'总条数: {sum(codes.values())}')
print(f'不同编码: {len(codes)}')
print()
for c, n in codes.most_common(20):
    print(f'  {c}: {n}')
print('  ...')
for c in sorted(codes.keys()):
    if '黑色' in c or '白色' in c or '定制' in c:
        print(f'  {c}: {codes[c]}')
