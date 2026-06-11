# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

# 各店铺规格模式
shops = {
    '淘宝品牌店': Counter(),
    '淘宝俊鑫': Counter(),
    '淘宝当下家': Counter(),
    '天猫扣底盒': Counter(),
    '天猫彩色': Counter(),
}

for r in rows:
    shop = str(r[0] or '').strip()
    name = str(r[3] or '').strip()[:60]
    if shop in shops:
        shops[shop][name] += 1

for shop, specs in shops.items():
    print(f"\n=== {shop} ({sum(specs.values())}条) ===")
    for s, c in specs.most_common(10):
        print(f"  [{c}] {s}")
