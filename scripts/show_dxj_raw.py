# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'

wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'), data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

dxj = [r for r in rows if '当下家' in str(r[0])]
print(f"当下家: {len(dxj)}条")

# 显示原文
for r in dxj[:3]:
    print(repr(str(r[3])))
