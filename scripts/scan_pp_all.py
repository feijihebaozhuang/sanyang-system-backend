# -*- coding: utf-8 -*-
"""扫描品牌店剩余所有规格"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

pp = [r for r in rows if '品牌店' in str(r[0]) and str(r[4]) != '无匹配']
print(f"品牌店(非无匹配): {len(pp)}条\n")

# 分组看模式
patterns = Counter()
for r in pp:
    patterns[str(r[3])[:80]] += 1

for p, c in patterns.most_common(200):
    print(f"  [{c:>3}] {p}")
