# -*- coding: utf-8 -*-
"""看平卡前几条的实际列内容"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
i = 0
for r in ws.iter_rows(min_row=1, max_row=10, values_only=True):
    print(f'行{i+1}: {[str(c)[:40] if c else "None" for c in r]}')
    i += 1
wb.close()
