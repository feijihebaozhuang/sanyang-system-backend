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
    # 看前几条的规格ID
    for i, r in enumerate(rows[:5]):
        print(f"  [{i}] 店铺={r[0]}, 商品id={r[1]}, 规格id={r[2]}, 编码={r[3]}")
    
    # 统计规格ID格式
    all_digits = sum(1 for r in rows if str(r[2] or '').strip().isdigit())
    has_alpha = sum(1 for r in rows if not str(r[2] or '').strip().isdigit() and str(r[2] or '').strip())
    empty = sum(1 for r in rows if not str(r[2] or '').strip())
    print(f"  纯数字规格ID: {all_digits}, 含字母: {has_alpha}, 空: {empty}")
    
    # 检查换绑文件里的对应商品ID有没有这个规格ID
    # 看有没有商品ID + 规格ID重复的
    pairs = {}
    for r in rows:
        key = f"{r[1]}|{r[2]}"
        pairs[key] = pairs.get(key, 0) + 1
    dup = {k:v for k,v in pairs.items() if v > 1}
    if dup:
        print(f"  重复 商品ID|规格ID: {len(dup)}个")
        for k,v in list(dup.items())[:3]:
            print(f"    {k}: {v}次")
