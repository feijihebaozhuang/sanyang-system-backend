# -*- coding: utf-8 -*-
"""看品牌店全部632条到底是什么"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

wb = oxl.load_workbook(r'd:\Desktop\换绑输出\平卡_待处理.xlsx', data_only=True)
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

pp = [r for r in rows if r and '品牌店' in str(r[0] or '')]
print(f'品牌店剩余: {len(pp)}')

# 分类
m2 = []; m10b = []; mc = []; other = []
for r in pp:
    spec = str(r[3] or '').strip()
    if re.search(r'[（(]宽[）)]', spec) and '外径' in spec:
        m2.append(r)
    elif '进口优质' in spec:
        m10b.append(r)
    elif '【' in spec and ('内径' in spec or '外径' in spec):
        mc.append(r)
    else:
        other.append(r)

print(f'模式A（宽+外径）: {len(m2)}')
print(f'模式B（进口优质）: {len(m10b)}')
print(f'模式C（【材料】）: {len(mc)}')
print(f'其他: {len(other)}')

if other:
    for r in other[:20]:
        print(f"  ? {str(r[3] or '')[:120]}")
