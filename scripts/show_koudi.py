# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

for r in rows:
    n = str(r[3] or '').strip()
    if '扣底盒' in r[0] and '30*30' in n:
        print(f"规格ID: {r[2]} | 规格: {n}")
