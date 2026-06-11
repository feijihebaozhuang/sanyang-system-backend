# -*- coding: utf-8 -*-
"""新鑫星 - 精确分类，每种一个例子"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
from collections import defaultdict

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

xx_items = [r for r in rows if r and str(r[0] or '').strip() == '阿里新鑫星']

groups = defaultdict(list)
for r in xx_items:
    spec = str(r[2] or '').strip()
    clean = spec.split(';')[0].strip() if ';' in spec else spec
    
    if re.match(r'^\d+[\s]*x\d+[\s]*cm\s*【长x宽】', clean, re.I):
        key = 'A类: XxY cm 【长x宽】'
    elif '外径扣抵盒' in clean:
        key = 'B类: XxYxZ；外径扣抵盒；材料'
    elif '外径白色高' in clean:
        key = 'C类: 外径白色高【Z厘米】；长x宽【XxY】'
    elif '纸箱' in clean and '外径五层' in clean:
        key = 'D类: 纸箱长X宽【XxY】；外径五层高度【ZCM】KK特硬'
    elif '外径双插盒' in clean or '外径双插' in clean:
        key = 'G类: XxYxZ；外径双插盒；材料'
    elif re.match(r'^长?\d+[\s]*(CM|cm)[；;]', clean, re.I):
        key = 'E类: 长X CM；宽Y cm；高Z cm'
    elif re.match(r'^\d+[\s]*(CM|cm)[；;]', clean, re.I):
        key = 'E类: 长X CM；宽Y cm；高Z cm'
    elif '长*宽' in clean:
        key = 'H类: 长*宽【XxY】尺寸'
    elif '长X宽' in clean:
        key = 'H类: 长X宽【XxY】尺寸'
    else:
        key = 'F类: 其他'
    
    groups[key].append(clean)

print(f'阿里新鑫星: {len(xx_items)}条')
print()
for key in sorted(groups.keys()):
    items = groups[key]
    example = items[0]
    print(f'{key} ({len(items)}条)')
    print(f'  例: {example}')
    print()
