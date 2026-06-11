# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

# 在平卡中搜索这些规格
keywords = ['优质进口纸-黄色', '双白色', '双面纯色', '37*14', '40.12*7']

for fname in ['平卡_待处理.xlsx', '无匹配_待处理.xlsx']:
    fp = os.path.join(out, fname)
    if not os.path.exists(fp):
        continue
    wb = oxl.load_workbook(fp, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()
    
    found = 0
    for r in rows:
        name = str(r[3] or '').strip()
        for kw in keywords:
            if kw in name:
                found += 1
                print(f"[{fname}] {name}")
                break
    print(f"  → {fname} 中找到 {found} 条\n")
