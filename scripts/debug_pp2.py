# -*- coding: utf-8 -*-
"""调试模式C匹配"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

RE_C = re.compile(
    r'【([^】]*)】\s*(内径|外径)\s*;\s*[【】\s]*(\d+\.?\d*)\s*x\s*(\d+\.?\d*)[】]*\s*;\s*(\d+\.?\d*)\s*cm?\s*高度'
)

wb = oxl.load_workbook(r'd:\Desktop\换绑输出\平卡_待处理.xlsx', data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

for r in rows:
    if not r: continue
    if '品牌店' not in str(r[0] or ''): continue
    spec = str(r[3] or '').strip()
    m = RE_C.search(spec)
    if m:
        print(f'✅ {spec[:80]}')
        print(f'   g1={m.group(1)} g2={m.group(2)} g3={m.group(3)} g4={m.group(4)} g5={m.group(5)}')
    else:
        print(f'❌ {spec[:80]}')
    break
