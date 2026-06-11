# -*- coding: utf-8 -*-
"""天猫彩色436条全部规格名称展示"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

color_items = [r for r in rows if r and str(r[0] or '').strip() == '天猫彩色']

# 统计每种规格
specs = Counter()
for r in color_items:
    spec = str(r[2] or '').strip()
    m = re.search(r'宽度[：:]\s*(\d+\.?\d*)\s*cm---高度[：:]\s*(\d+\.?\d*)\s*cm;.*?长度[：:]\s*(\d+\.?\d*)\s*cm', spec)
    if m:
        w = m.group(1); h = m.group(2); l = m.group(3)
        specs[f'宽{w}cm 高{h}cm 长{l}cm'] += 1

print(f'天猫彩色总数: {len(color_items)}条')
print(f'不同规格数: {len(specs)}')
print()

# 按宽度分组
by_w = Counter()
for k in specs:
    w = k.split()[0].replace('宽','').replace('cm','')
    by_w[float(w)] += specs[k]

print('按宽度分组:')
for w in sorted(by_w.keys()):
    print(f'  宽{w}cm: {by_w[w]}条')

# 按高度分组
by_h = Counter()
for k in specs:
    h = k.split()[1].replace('高','').replace('cm','')
    by_h[float(h)] += specs[k]

print('\n按高度分组:')
for h in sorted(by_h.keys()):
    print(f'  高{h}cm: {by_h[h]}条')

# 全部规格
print(f'\n全部{len(specs)}种规格:')
for k in sorted(specs.keys(), key=lambda x: (float(x.split()[0].replace('宽','').replace('cm','')), 
                                               float(x.split()[2].replace('长','').replace('cm','')))):
    print(f'  {k}')
