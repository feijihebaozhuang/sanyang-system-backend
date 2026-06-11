# -*- coding: utf-8 -*-
"""显示平卡各店铺样本"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

# 按店铺
from collections import defaultdict
by_shop = defaultdict(list)
for r in rows:
    if not r or not r[0]: continue
    shop = str(r[0]).strip()
    by_shop[shop].append(r)

for shop, items in sorted(by_shop.items()):
    print(f'\n{"="*60}')
    print(f'{shop}: {len(items)}条')
    print(f'{"="*60}')
    # 显示5条样本
    for r in items[:5]:
        spec_name = str(r[2] or '').strip() if len(r) >= 3 else ''
        spec_id = str(r[3] or '').strip() if len(r) >= 4 else ''
        print(f'  规格名称: {spec_name[:80]}')
        print(f'  规格id: {spec_id}')
        print()
