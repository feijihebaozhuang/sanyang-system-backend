# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

# 搜天猫相关
tianmao = [r for r in rows if '天猫' in str(r[0]) or '淘宝' in str(r[0])]
print(f"天猫/淘宝店铺在平卡中: {len(tianmao)}条")

from collections import Counter
shops = Counter()
for r in tianmao:
    shops[str(r[0])] += 1

for s, c in shops.most_common():
    print(f"  [{c}] {s}")
    # 显示前2条
    samples = [r for r in tianmao if r[0] == s][:2]
    for r in samples:
        print(f"     {r[1]} | {str(r[3])[:60]}")
