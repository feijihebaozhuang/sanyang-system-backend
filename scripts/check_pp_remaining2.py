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

pp = [r for r in rows if '品牌店' in str(r[0])]
print(f"品牌店: {len(pp)}条")

# 按原因分
reasons = Counter()
for r in pp:
    reasons[str(r[4])] += 1
print(f"原因分布: {dict(reasons)}")

# 看无匹配的
nomatch = [r for r in pp if str(r[4]) == '无匹配']
other = [r for r in pp if str(r[4]) != '无匹配']
print(f"\n无匹配: {len(nomatch)}条")
print(f"其他: {len(other)}条")

if other:
    patterns = Counter()
    for r in other[:50]:
        patterns[str(r[3])[:80]] += 1
    print(f"\n其他(前50):")
    for p, c in patterns.most_common(20):
        print(f"  [{c}] {p}")
