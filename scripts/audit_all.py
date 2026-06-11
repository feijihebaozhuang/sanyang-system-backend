# -*- coding: utf-8 -*-
"""快速审计桌面所有换绑文件的定制链接率"""
import sys, pandas as pd, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

desktop = r'D:\Desktop'
files = sorted([f for f in os.listdir(desktop) if f.startswith('换绑') and f.endswith('.xlsx') and '部分' not in f])

print(f'{"文件":40s} {"条数":>6s} {"定制":>6s} {"%":>6s}')
print('-' * 60)

for fname in files:
    fpath = os.path.join(desktop, fname)
    try:
        df = pd.read_excel(fpath, dtype=str, skiprows=1)
    except:
        print(f'{fname:40s} 读取失败'); continue
    if df.empty: print(f'{fname:40s} {"空":>18s}'); continue
    
    # 找到商品编码列
    col_map = {}
    for c in df.columns:
        if '商品编码' in str(c): col_map['code'] = c
        if '店铺' in str(c): col_map['shop'] = c
    
    total = len(df)
    code_col = col_map.get('code', df.columns[-1])
    custom = (df[code_col].astype(str).str.strip() == '定制链接').sum()
    pct = custom/total*100
    
    marker = ' ❗' if pct > 2 else ' ✅' if pct == 0 else ' ⚠️'
    print(f'{fname:40s} {total:>6d} {custom:>6d} {pct:>5.1f}%{marker}')
