# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

# 读取尺寸不足的文件
wb = oxl.load_workbook(os.path.join(out, '尺寸不足_待处理.xlsx'), data_only=True)
ws = wb['尺寸不足']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

print(f"尺寸不足总数: {len(rows)}", flush=True)

# 统计规格名称模式
from collections import Counter
specs = Counter()
for r in rows:
    name = str(r[3] or '').strip()
    specs[name[:60]] += 1

print(f"\n不同规格模式: {len(specs)}")
print("\n出现最多的规格名:")
for name, cnt in specs.most_common(50):
    print(f"  [{cnt:>4}] {name}")
