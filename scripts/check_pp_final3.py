# -*- coding: utf-8 -*-
"""检查平卡品牌店哪些没被RE_C匹配"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

RE_C = re.compile(r'【([^】]*)】\s*(内径|外径)\s*;\s*[【】\s]*(\d+)\s*x\s*(\d+)[】]*\s*;\s*(\d+)\s*cm\s*高度')

wb = oxl.load_workbook(r'd:\Desktop\换绑输出\平卡_待处理.xlsx', data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

pp = [r for r in rows if r and '品牌店' in str(r[0] or '')]

matched = 0
unmatched = 0
for r in pp:
    spec = str(r[3] or '').strip()
    m = RE_C.search(spec)
    if m:
        matched += 1
    else:
        unmatched += 1
        if unmatched <= 5:
            print(f'未匹配: {spec[:150]}')

print(f'\n匹配RE_C: {matched}')
print(f'未匹配RE_C: {unmatched}')
