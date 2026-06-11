# -*- coding: utf-8 -*-
"""检查模式C 630条中内外径分布"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

wb = oxl.load_workbook(r'd:\Desktop\换绑输出\平卡_待处理.xlsx', data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

pp = [r for r in rows if r and '品牌店' in str(r[0] or '')]

dk_count = Counter()
for r in pp:
    spec = str(r[3] or '').strip()
    if '【' in spec and ('内径' in spec or '外径' in spec):
        m = re.search(r'【([^】]*)】\s*(内径|外径)\s*;', spec)
        if m:
            dk = m.group(2)
            dk_count[dk] += 1

out = []
out.append(f'品牌店剩余: {len(pp)}')
out.append(f'')
out.append(f'内外径分布:')
for k,v in dk_count.most_common():
    out.append(f'  {k}: {v}')

# 看进口优质2条
for r in pp:
    spec = str(r[3] or '').strip()
    if '进口优质' in spec:
        out.append(f'')
        out.append(f'进口优质: {spec}')

for line in out:
    print(line)
