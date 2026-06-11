# -*- coding: utf-8 -*-
"""新鑫星 - 按格式分类，每种只发一个例子"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl

out = r'd:\Desktop\换绑输出'
wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
ws = wb['平卡']
rows = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

xx_items = [r for r in rows if r and str(r[0] or '').strip() == '阿里新鑫星']

groups = {}
for r in xx_items:
    spec = str(r[2] or '').strip()
    clean = spec.split(';')[0].strip() if ';' in spec else spec
    
    # 判断类别
    if re.match(r'^\d+[\s]*x\d+[\s]*cm\s*【长x宽】', clean, re.I):
        key = 'A类: XxY cm 【长x宽】'
    elif '外径扣抵盒' in clean or '外径扣抵盒' in clean:
        key = 'B类: XxYxZ；外径扣抵盒；材料(双面黄/双面白)'
    elif '外径白色高' in clean:
        key = 'C类: 外径白色高【Z厘米】；长x宽【XxY】'
    elif '纸箱' in clean and '外径五层' in clean:
        key = 'D类: 纸箱长X宽【XxY】；外径五层高度【ZCM】KK特硬'
    elif re.match(r'^长?\d+[\s]*(CM|cm)[；;]', clean, re.I) or re.match(r'^\d+[\s]*(CM|cm)[；;]', clean, re.I):
        key = 'E类: 长X CM；宽Y cm；高Z cm'
    else:
        key = 'F类: 其他'
    
    if key not in groups:
        groups[key] = (clean, r)

print(f'阿里新鑫星: {len(xx_items)}条')
print()
for key in sorted(groups.keys()):
    clean, r = groups[key]
    # 统计这类有多少条
    count = 0
    for r2 in xx_items:
        s2 = str(r2[2] or '').strip()
        c2 = s2.split(';')[0].strip() if ';' in s2 else s2
        if key.startswith('A类') and re.match(r'^\d+[\s]*x\d+[\s]*cm\s*【长x宽】', c2, re.I): count += 1
        elif key.startswith('B类') and ('外径扣抵盒' in c2 or '外径扣抵盒' in s2): count += 1
        elif key.startswith('C类') and '外径白色高' in c2: count += 1
        elif key.startswith('D类') and '纸箱' in c2 and '外径五层' in c2: count += 1
        elif key.startswith('E类') and (re.match(r'^长?\d+[\s]*(CM|cm)[；;]', c2, re.I) or re.match(r'^\d+[\s]*(CM|cm)[；;]', c2, re.I)): count += 1
        elif not any(key.startswith(x) for x in ['A类','B类','C类','D类','E类']): count += 1
    
    print(f'{key} ({count}条)')
    print(f'  例: {clean}')
    print()
