# -*- coding: utf-8 -*-
"""全面调试品牌店处理"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

RE_B = re.compile(
    r'进口优质.*?(内径|外经|外径)\s*;\s*长x宽[【】\s]*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)\s*mm?[】]*\s*;\s*(\d+\.?\d*)\s*mm?'
)
RE_C = re.compile(
    r'【([^】]*)】\s*(内径|外径)\s*;\s*[【】\s]*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)[】]*\s*;\s*(\d+\.?\d*)\s*cm?\s*高度'
)

wb = oxl.load_workbook(r'd:\Desktop\换绑输出\平卡_待处理.xlsx', data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

b_ok = 0
c_ok = 0
none_count = 0
for r in rows:
    if not r: continue
    if '品牌店' not in str(r[0] or ''): continue
    spec = str(r[3] or '').strip()
    
    if RE_B.search(spec):
        b_ok += 1
    elif RE_C.search(spec):
        c_ok += 1
    else:
        none_count += 1
        if none_count <= 3:
            print(f'未匹配: {spec[:120]}')

print(f'\n模式B匹配: {b_ok}')
print(f'模式C匹配: {c_ok}')
print(f'均不匹配: {none_count}')
