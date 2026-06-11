# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

for fn in ['定制类_换绑文件.xlsx', '定制类_换绑文件_第2批.xlsx']:
    fp = os.path.join(out, fn)
    wb = oxl.load_workbook(fp, data_only=True)
    ws = wb['Sheet1']
    rows = list(ws.iter_rows(min_row=3, values_only=True))
    wb.close()
    
    print(f"\n=== {fn} ({len(rows)}条) ===")
    shops = {}
    for r in rows:
        name = str(r[0] or '').strip()
        shops[name] = shops.get(name, 0) + 1
    
    for s, c in sorted(shops.items(), key=lambda x: -x[1]):
        print(f"  [{c:>4}] {s}")
    
    # 检查前几条规格ID格式
    print(f"\n  前3条数据:")
    for i, r in enumerate(rows[:3]):
        print(f"    [{i}] 店铺={r[0]}, 商品ID={r[1]}, 规格ID={r[2]}, 编码={r[3]}")
