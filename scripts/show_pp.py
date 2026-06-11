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

pp = [(str(r[3] or '').strip(), r) for r in rows if '品牌店' in str(r[0])]
print(f"品牌店: {len(pp)}条", flush=True)

patterns = Counter()
for name, r in pp:
    patterns[name[:80]] += 1

for p, c in patterns.most_common(100):
    print(f"  [{c:>3}] {p}")
