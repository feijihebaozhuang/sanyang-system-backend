# -*- coding: utf-8 -*-
"""看品牌店剩余 576条详情"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

wb = oxl.load_workbook(r'd:\Desktop\换绑输出\品牌店_待确认.xlsx', data_only=True)
ws = wb['待确认']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

print(f'待确认条数: {len(rows)}')

# 分类
patterns = Counter()
for r in rows:
    spec = str(r[3] or '').strip()
    m = re.search(r'宽度[【】\s]*(\d+\.?\d*)\s*\*+\s*(\d+\.?\d*)\s*', spec)
    m_l = re.search(r'长度\s*(\d+\.?\d*)\s*cm', spec)
    if m and m_l:
        w = float(m.group(1))
        h = float(m.group(2))
        l = float(m_l.group(1))
        patterns[f'宽{w}cm*高{h}cm 长{l}cm'] += 1
    else:
        patterns[f'其他: {spec[:60]}'] += 1

print(f'\n不同规格数: {len(patterns)}')
for k, v in sorted(patterns.items(), key=lambda x: -x[1])[:30]:
    print(f'  [{v}条] {k}')
if len(patterns) > 30:
    print(f'  ... 还有{len(patterns)-30}种')
