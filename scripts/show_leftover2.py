# -*- coding: utf-8 -*-
"""显示平卡中天猫/淘宝遗留数据的规格名称"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

# 平卡列：店铺简称(0), 平台商品id(1), 平台规格id(2), 规格名称(3), 原因(4), 期望编码(5)
non_ali = ['天猫小批量', '天猫彩色', '天猫扣底盒', '天猫止合', '天猫正方形',
           '淘宝俊鑫', '淘宝品牌店', '淘宝当下家']

for shop in non_ali:
    items = [r for r in rows if r and str(r[0] or '').strip() == shop]
    if not items: continue
    print(f'\n{"="*60}')
    print(f'{shop}: {len(items)}条')
    print(f'{"="*60}')
    # 看规格名称(第4列,索引3)
    specs = Counter()
    for r in items:
        spec = str(r[3] or '').strip() if len(r) >= 4 else ''
        prefix = spec[:50] if len(spec) > 50 else spec
        specs[prefix] += 1
    print(f'规格名称前20种:')
    for p, c in specs.most_common(20):
        print(f'  [{c:>4}] {p}')
