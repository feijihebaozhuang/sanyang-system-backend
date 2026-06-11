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

dxj = [(str(r[3] or '').strip(), str(r[1] or '').strip()) for r in rows if '当下家' in str(r[0])]
print(f"当下家: {len(dxj)}条", flush=True)

patterns = Counter()
for name, pid in dxj:
    patterns[name[:80]] += 1

for p, c in patterns.most_common(50):
    print(f"  [{c:>3}] {p}")
