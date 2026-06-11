# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

wb = oxl.load_workbook(r'D:\Desktop\换绑_深圳市大鱼包装材料有限公司.xlsx')
ws = wb.active

codes = Counter()
for row in ws.iter_rows(min_row=3, values_only=True):
    codes[str(row[3] or '')] += 1
wb.close()

print(f'总条数: {sum(codes.values())}')
print(f'不同编码: {len(codes)}')
print()

# 找纸箱的
for c, n in codes.most_common(5):
    print(f'  {c}: {n}')
print('  ...')
# 看黑色、白色的
for c, n in sorted(codes.items()):
    if '黑色' in c or '白色' in c or 'B' in c.split('-')[-1]:
        print(f'  {c}: {n}')
