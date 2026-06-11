# -*- coding: utf-8 -*-
"""检查品牌店和天猫彩色是否全部统一格式"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

# 品牌店检查
pp_items = [r for r in rows if r and str(r[0] or '').strip() == '淘宝品牌店']
print(f'品牌店: {len(pp_items)}条')

pp_patterns = Counter()
for r in pp_items:
    spec = str(r[2] or '').strip()
    m = re.search(r'【([^】]*)】\s*(内径|外径)\s*;\s*[【】\s]*(\d+)\s*x\s*(\d+)[】]*\s*;\s*(\d+)\s*cm', spec)
    if m:
        pp_patterns[f'【{m.group(1)}】{m.group(2)} {m.group(3)}x{m.group(4)}x{m.group(5)}cm'] += 1
    else:
        pp_patterns[f'其他: {spec[:60]}'] += 1

print(f'不同模式: {len(pp_patterns)}')
for p, c in pp_patterns.most_common(20):
    print(f'  [{c:>4}] {p}')

# 天猫彩色检查
color_items = [r for r in rows if r and str(r[0] or '').strip() == '天猫彩色']
print(f'\n天猫彩色: {len(color_items)}条')

color_patterns = Counter()
for r in color_items:
    spec = str(r[2] or '').strip()
    m = re.search(r'宽度[：:]\s*(\d+\.?\d*)\s*cm---高度[：:]\s*(\d+\.?\d*)\s*cm;.*?长度[：:]\s*(\d+\.?\d*)\s*cm', spec)
    if m:
        color_patterns[f'宽{m.group(1)}cm 高{m.group(2)}cm 长{m.group(3)}cm'] += 1
    else:
        color_patterns[f'其他: {spec[:60]}'] += 1

print(f'不同规格: {len(color_patterns)}')
for p, c in color_patterns.most_common(20):
    print(f'  [{c:>4}] {p}')

# 天猫小批量3条
print(f'\n天猫小批量: 3条')
for r in [r for r in rows if r and str(r[0] or '').strip() == '天猫小批量']:
    spec = str(r[2] or '').strip()
    print(f'  {spec}')
