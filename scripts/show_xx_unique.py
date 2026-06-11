# -*- coding: utf-8 -*-
"""新鑫星 - 完整规格名称，每种格式只发一条"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import OrderedDict

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

xx_items = [r for r in rows if r and str(r[0] or '').strip() == '阿里新鑫星']

seen = OrderedDict()
for r in xx_items:
    spec = str(r[2] or '').strip()
    if spec not in seen:
        seen[spec] = True
        print(spec)
