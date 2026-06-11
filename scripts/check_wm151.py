# -*- coding: utf-8 -*-
"""看待确认151条详情"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

wb = oxl.load_workbook(r'd:\Desktop\换绑输出\品牌店_待确认.xlsx', data_only=True)
ws = wb['待确认']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

print(f'待确认: {len(rows)}条')

# 查看格式分类
cats = Counter()
for r in rows:
    spec = str(r[3] or '').strip()
    expect = str(r[5] or '').strip() if len(r) >= 6 else ''
    if '宽度' in spec and '长度' in spec:
        cats['宽度【】长度'] += 1
    elif '【' in spec:
        cats['【材料】格式'] += 1
    else:
        cats[f'其他: {spec[:40]}'] += 1

for k,v in cats.most_common():
    print(f'  [{v}] {k}')

# 看前10条
print(f'\n前10条:')
for r in rows[:10]:
    spec = str(r[3] or '')[:100]
    expect = str(r[5] or '')[:50] if len(r) >= 6 else ''
    print(f'  {spec} -> {expect}')
