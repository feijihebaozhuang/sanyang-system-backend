# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '定制类_换绑文件.xlsx'), data_only=True)
ws = wb['Sheet1']
rows = list(ws.iter_rows(min_row=3, values_only=True))
wb.close()

from collections import Counter
shops = Counter()
for r in rows:
    shops[str(r[0])] += 1

print("定制类_换绑文件.xlsx 当前店铺名称分布:")
for name, cnt in shops.most_common():
    print(f"  [{cnt:>4}] {name}")
