# -*- coding: utf-8 -*-
"""阿里新鑫星 - 按格式分类展示所有种类"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import Counter, defaultdict

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

xx_items = [r for r in rows if r and str(r[0] or '').strip() == '阿里新鑫星']

# 分组
groups = defaultdict(list)

for r in xx_items:
    spec = str(r[2] or '').strip()
    
    # 长 CM；宽 cm；高 cm 类型
    if re.match(r'^长?\d+[\s]*CM[；;]', spec):
        groups['类型1: 长X CM;宽Y cm;高Z cm'].append(r)
    elif re.match(r'^\d+[\s]*CM[；;]', spec):
        # 44 CM；宽 10 cm；高 3 cm
        groups['类型1b: X CM;宽Y cm;高Z cm'].append(r)
    elif '扣抵盒' in spec or '扣底盒' in spec:
        groups['类型2: 扣底盒'].append(r)
    elif '外径' in spec or '内径' in spec:
        groups['类型3: 内/外径'].append(r)
    elif '长宽' in spec or '长*宽' in spec:
        groups['类型4: 长宽格式'].append(r)
    else:
        groups['类型5: 其他'].append(r)

print(f'阿里新鑫星总数: {len(xx_items)}条')
print(f'\n{"="*60}')

for gname, items in sorted(groups.items()):
    print(f'\n--- {gname}: {len(items)}条 ---')
    # 展示所有不同规格
    seen = set()
    for r in items:
        spec = str(r[2] or '').strip()
        key = spec[:80]
        if key not in seen:
            seen.add(key)
            print(f'  {spec[:120]}')
    print(f'  共{len(seen)}种')
