# -*- coding: utf-8 -*-
"""查看当前平卡店铺分布"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

shops = Counter()
for r in rows:
    if not r: continue
    shop = str(r[0] or '').strip()
    if shop:
        shops[shop] += 1

print(f'平卡总条数: {len([r for r in rows if r])}')
print(f'\n店铺分布:')
for shop, cnt in shops.most_common(30):
    print(f'  [{cnt:>6}] {shop}')
