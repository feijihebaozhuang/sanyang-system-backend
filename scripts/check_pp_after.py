# -*- coding: utf-8 -*-
"""检查当前平卡中品牌店剩余"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

wb = oxl.load_workbook(r'd:\Desktop\换绑输出\平卡_待处理.xlsx', data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

pp = [r for r in rows if r and '品牌店' in str(r[0] or '')]
print(f'品牌店剩余: {len(pp)}')
for r in pp[:20]:
    spec = str(r[3] or '')[:120]
    print(f'  {spec}')
