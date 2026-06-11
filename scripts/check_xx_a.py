# -*- coding: utf-8 -*-
"""查新鑫星 A类 12x12 cm 【长x宽】的完整信息"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

for r in rows:
    if not r: continue
    shop = str(r[0] or '').strip()
    spec = str(r[2] or '').strip()
    if shop == '阿里新鑫星' and '12x12 cm 【长x宽】' in spec:
        pid = str(r[1] or '').strip()
        spec_id = str(r[3] or '').strip()
        print(f'规格名称: {spec}')
        print(f'平台商品id: {pid}')
        print(f'平台规格id: {spec_id}')
        break
