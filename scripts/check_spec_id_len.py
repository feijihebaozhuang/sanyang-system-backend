# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

# 检查定制1里的规格ID长度分布
wb = oxl.load_workbook(os.path.join(out, '定制类_换绑文件.xlsx'), data_only=True)
ws = wb['Sheet1']
rows = list(ws.iter_rows(min_row=3, values_only=True))
wb.close()

from collections import Counter
lens = Counter()
for r in rows:
    sid = str(r[2] or '').strip()
    lens[len(sid)] += 1

print("规格ID长度分布:")
for l, c in sorted(lens.items()):
    print(f"  长度{l}: {c}条")

# 看一下友尚那条的实际长度
for r in rows:
    if '友尚' in str(r[0]) and str(r[1]).strip() == '535958072829':
        print(f"\n友尚 535958072829 的规格ID: [{r[2]}] (长度{len(str(r[2]).strip())})")
        break

# 对比原始长度
print("\n原始数据中 友尚 535958072829 的规格ID:")
print("  a845ef7236480bd273e338021892f922535958072829 (长度50)")
