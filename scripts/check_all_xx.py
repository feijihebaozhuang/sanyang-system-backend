# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd, re

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('新鑫星', na=False)
df2 = df[mask]

km_file = r'd:\Desktop\快麦商品 - 副本.xlsx'
km = pd.read_excel(km_file, sheet_name='报表1', header=3, dtype=str, usecols=[0])
km_codes = set()
for row in km.values:
    code = str(row[0] or '').strip()
    if code: km_codes.add(code)

print('=== 剩余新鑫星 %d条 ===\n' % len(df2))

for _, row in df2.iterrows():
    s = str(row['规格名称'])
    sid = str(row['平台规格id'])
    found = False
    
    # 1. 型号类 A1: 10*6.5*5.5cm；E瓦特硬
    m = re.search(r'[\w]+[:：]\s*([\d.]+)\s*\*\s*([\d.]+)\s*\*\s*([\d.]+)\s*cm', s)
    if m:
        dims = sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True)
        code = f"{dims[0]:g}*{dims[1]:g}*{dims[2]:g}-外径-特硬"
        if code in km_codes:
            print('  ✅ %s' % code)
        else:
            print('  ❌ %s → 无匹配' % code)
        continue
    
    # 2. 28*27*11；D6D【特硬】类型
    m2 = re.search(r'^([\d.]+)\s*\*\s*([\d.]+)\s*\*\s*([\d.]+)\s*[；;]', s)
    if m2:
        dims = sorted([float(m2.group(1)), float(m2.group(2)), float(m2.group(3))], reverse=True)
        code = f"{dims[0]:g}*{dims[1]:g}*{dims[2]:g}-外径-特硬"
        if code in km_codes:
            print('  ✅ %s' % code)
        else:
            print('  ❌ %s → 无匹配' % code)
        continue
    
    # 3. E类 长XX CM；宽XXCM；高度XXCM
    m3 = re.search(r'长?([\d.]+)\s*CM[；;]\s*宽\s*([\d.]+)\s*CM[；;]\s*高度([\d.]+)\s*CM', s)
    if m3:
        l, w, h = float(m3.group(1)), float(m3.group(2)), float(m3.group(3))
        dims = sorted([l, w, h], reverse=True)
        
        # 先试外径-特硬
        code = f"{dims[0]:g}*{dims[1]:g}*{dims[2]:g}-外径-特硬"
        if code in km_codes:
            print('  ✅ %s (外径)' % code)
            continue
        
        # 再试内径
        il, iw, ih = dims[0]-1.5, dims[1]-0.5, dims[2]-0.5
        if il > 0:
            code_i = f"{il:g}*{iw:g}*{ih:g}-内径-特硬"
            if code_i in km_codes:
                print('  ✅ %s (内径)' % code_i)
                continue
        
        print('  ❌ 外径:%s 内径:%s → 均无匹配' % (code, f"{il:g}*{iw:g}*{ih:g}-内径-特硬" if il > 0 else 'N/A'))
        continue
    
    print('  ❓ 未识别: %s' % s[:60])
