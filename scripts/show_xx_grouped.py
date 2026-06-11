# -*- coding: utf-8 -*-
"""阿里新鑫星 - 按格式分组展示"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import defaultdict, Counter

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

xx_items = [r for r in rows if r and str(r[0] or '').strip() == '阿里新鑫星']

print(f'阿里新鑫星: {len(xx_items)}条')
print()

# 按格式分类
groups = defaultdict(list)

for r in xx_items:
    spec = str(r[2] or '').strip()
    # 去掉分号后的重复部分
    clean = spec.split(';')[0].strip() if ';' in spec else spec
    
    # 分类
    if re.match(r'^\d+[\s]*x\d+[\s]*cm\s*【长x宽】', clean, re.I):
        groups['A: XxY cm 【长x宽】'].append(clean)
    elif '外径' in clean and '扣抵盒' in clean:
        groups['B: XxYxZ；外径扣抵盒100个；材料'].append(clean)
    elif '外径白色' in clean and '长x宽' in clean:
        groups['C: 外径白色高【Z厘米】；长x宽【XxY】'].append(clean)
    elif re.match(r'^长?\d+[\s]*(CM|cm)[；;]', clean):
        groups['D: 长X CM；宽Y cm；高Z cm'].append(clean)
    elif re.match(r'^\d+[\s]*(CM|cm)[；;]', clean):
        groups['D: 长X CM；宽Y cm；高Z cm'].append(clean)
    else:
        groups['E: 其他'].append(clean)

for gname, items in sorted(groups.items()):
    print(f'\n--- {gname}: {len(items)}条 ---')
    # 展示所有不同规格
    seen = sorted(set(items))
    for s in seen:
        print(f'  {s}')
