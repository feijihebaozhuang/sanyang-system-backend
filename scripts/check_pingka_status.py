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

print(f"平卡总数: {len(rows)}", flush=True)

shops = Counter()
reasons = Counter()
for r in rows:
    shops[str(r[0])] += 1
    reasons[str(r[4])] += 1

print("\n店铺分布:")
for s, c in shops.most_common():
    print(f"  [{c:>5}] {s}")

print("\n原因分布:")
for s, c in reasons.most_common():
    print(f"  [{c:>5}] {s}")
