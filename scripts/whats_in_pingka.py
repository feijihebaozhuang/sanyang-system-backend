# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

print(f"平卡总数: {len(rows)}", flush=True)

# 店铺分布
from collections import Counter
shops = Counter()
for r in rows:
    shops[str(r[0])] += 1

print("\n店铺分布:")
for s, c in shops.most_common():
    print(f"  [{c:>5}] {s}")

# 还有扣底盒吗？
koudi = [r for r in rows if '扣底盒' in str(r[0])]
print(f"\n扣底盒: {len(koudi)}条")
for r in koudi[:5]:
    print(f"  {r[1]} | {r[3][:60]}")

# 还有止合吗？
zhige = [r for r in rows if '止合' in str(r[0])]
print(f"\n止合: {len(zhige)}条")
for r in zhige[:5]:
    print(f"  {r[1]} | {r[3][:60]}")

# 还有彩色吗？
caise = [r for r in rows if '彩色' in str(r[0])]
print(f"\n彩色: {len(caise)}条")
for r in caise[:5]:
    print(f"  {r[1]} | {r[3][:60]}")
