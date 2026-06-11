# -*- coding: utf-8 -*-
"""显示平卡中天猫/淘宝遗留数据的样本"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

# 非阿里的店铺
non_ali = ['天猫小批量', '天猫彩色', '天猫扣底盒', '天猫止合', '天猫正方形', 
           '淘宝俊鑫', '淘宝品牌店', '淘宝当下家']

for shop in non_ali:
    items = [r for r in rows if r and str(r[0] or '').strip() == shop]
    if not items: continue
    print(f'\n{"="*60}')
    print(f'{shop}: {len(items)}条')
    print(f'{"="*60}')
    # 看规格名称的前缀分布
    prefixes = Counter()
    for r in items:
        spec = str(r[3] or '').strip()
        prefix = spec[:30] if len(spec) > 30 else spec
        prefixes[prefix] += 1
    print(f'前20种规格名称前缀:')
    for p, c in prefixes.most_common(20):
        print(f'  [{c:>4}] {p}')
