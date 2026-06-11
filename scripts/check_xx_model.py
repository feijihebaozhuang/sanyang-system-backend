# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('新鑫星', na=False)
df2 = df[mask]

# 筛选E类之外的非分类21条
unmask = ~df2['规格名称'].str.match(r'长?[\d.]+', na=False)
others = df2[unmask]

km_file = r'd:\Desktop\快麦商品 - 副本.xlsx'
km = pd.read_excel(km_file, sheet_name='报表1', header=3, dtype=str, usecols=[0,1,2])
km_codes = set()
for row in km.values:
    code = str(row[0] or '').strip()
    if code: km_codes.add(code)

print('=== 型号类21条匹配检测 ===\n')
for _, row in others.iterrows():
    s = str(row['规格名称'])
    # 型号类: A12：17.5*15*8.5cm；E瓦特硬
    m = re.search(r'[\w]+[:：]\s*([\d.]+)\*([\d.]+)\*([\d.]+)\s*cm', s)
    if m:
        dims = sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True)
        code_outer = f"{dims[0]:g}*{dims[1]:g}*{dims[2]:g}-外径-特硬"
        code_inner = f"{dims[0]-1.5:g}*{dims[1]-0.5:g}*{dims[2]-0.5:g}-内径-特硬"
        if code_outer in km_codes:
            print('  ✅ %s → %s' % (s[:50], code_outer))
        elif code_inner in km_codes:
            print('  🔄 %s → %s (内径)' % (s[:50], code_inner))
        else:
            print('  ❌ %s → 外径:%s 内径:%s 均无' % (s[:50], code_outer, code_inner))
        continue
    
    # 28*27*11；D6D【特硬】；牛皮色 三层E瓦
    m2 = re.search(r'([\d.]+)\s*\*\s*([\d.]+)\s*\*\s*([\d.]+)\s*[；;]', s)
    if m2:
        dims = sorted([float(m2.group(1)), float(m2.group(2)), float(m2.group(3))], reverse=True)
        code = f"{dims[0]:g}*{dims[1]:g}*{dims[2]:g}-外径-特硬"
        if code in km_codes:
            print('  ✅ %s → %s' % (s[:50], code))
        else:
            print('  ❌ %s → %s 无匹配' % (s[:50], code))
        continue
    
    print('  ❓ 未识别: %s' % s[:60])
