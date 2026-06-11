# -*- coding: utf-8 -*-
"""阿里新鑫星 - 按规格名称归类展示"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

xx_items = [r for r in rows if r and str(r[0] or '').strip() == '阿里新鑫星']

print(f'阿里新鑫星: {len(xx_items)}条')
print()

# 按规格名称前缀（去掉重复部分）分组
# 大部分格式是: "前半部分;后半部分" 后半部分是重复的
# 取完整规格名称展示
specs = Counter()
for r in xx_items:
    spec = str(r[2] or '').strip()
    # 去掉分号后的重复部分（如果有的话）
    clean = spec.split(';')[0] if ';' in spec else spec
    specs[clean] += 1

# 按条数从多到少打印
for k, v in specs.most_common():
    print(f'  [{v:>4}] {k}')
