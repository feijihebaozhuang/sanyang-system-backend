# -*- coding: utf-8 -*-
"""只找这5个有疑问的数据：店铺名+商品ID+规格ID+规格名称"""
import openpyxl, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

fp = r"d:\Desktop\平台商品.xlsx"
wb = openpyxl.load_workbook(fp, read_only=True, data_only=True)
ws = wb['报表1']

keys = {
    'A4': '长【100】cm；宽【10】cm；3层原色【E坑1.7mm】',
    'A6': 'mm 长【外径】',
    'B7': '长26 CM',
    'C1': '【双面白】【100个】;',
    'C4': '特硬【双面白色】100个',
}

found = {k: 0 for k in keys}

for i, row in enumerate(ws.iter_rows(min_row=3, values_only=True)):
    shop, pid, spec_name, spec_id = row
    if not spec_name:
        continue
    s = str(spec_name).strip()
    
    for key, pattern in keys.items():
        if found[key] >= 3:
            continue
        if pattern in s:
            found[key] += 1
            print(f"{key}: 店铺={shop}, 商品id={pid}, 规格id={spec_id}")
            print(f"   规格: {s[:100]}")
            print()
    
    if all(v >= 3 for v in found.values()):
        break

wb.close()

for k, v in found.items():
    print(f"{k}: 找到 {v} 条")
