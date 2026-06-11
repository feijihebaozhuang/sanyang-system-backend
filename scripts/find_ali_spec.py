# -*- coding: utf-8 -*-
import sys, os, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pf = r'd:\Desktop\平台商品.xlsx'

# 搜索这个规格ID
df = pd.read_excel(pf, sheet_name='报表1', header=None, dtype=str)
print(f"总行数: {len(df)}", flush=True)

# 在第4列找这个ID
target = 'a845ef7236480bd273e338021892f922535958072829'
found = 0
for i in range(3, len(df)):
    row = df.iloc[i].values
    if len(row) >= 4 and str(row[3] or '').strip() == target:
        found += 1
        print(f"\n找到! 第{i}行:")
        for j, v in enumerate(row):
            print(f"  列{j}: {str(v)[:60]}")
        if found >= 3:
            break

if found == 0:
    print(f"未找到 {target}")
    # 搜索部分匹配
    for i in range(3, min(1000, len(df))):
        row = df.iloc[i].values
        if len(row) >= 4 and target[:10] in str(row[3] or ''):
            print(f"部分匹配 第{i}行: {[str(x)[:30] for x in row]}")
            break
