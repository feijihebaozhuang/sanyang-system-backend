# -*- coding: utf-8 -*-
"""调试品牌店632条的处理"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl, re

wb = oxl.load_workbook(r'd:\Desktop\换绑输出\平卡_待处理.xlsx', data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

pp_count = 0
non_pp_remain = 0
for r in rows:
    if not r: continue
    shop = str(r[0] or '').strip()
    if '品牌店' in shop:
        pp_count += 1
    else:
        non_pp_remain += 1

print(f"品牌店: {pp_count}")
print(f"非品牌店: {non_pp_remain}")
print(f"总: {pp_count + non_pp_remain}")
