# -*- coding: utf-8 -*-
import sys, os, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pf = r'd:\Desktop\平台商品.xlsx'

# 直接用pandas读，跟脚本一样的方式
df = pd.read_excel(pf, sheet_name='报表1', header=2, dtype=str)
print(f"总行数: {len(df)}", flush=True)
print(f"列名: {list(df.columns)}", flush=True)

# 搜索目标规格ID
targets = [
    '13a2205db4ffda89c08e811dd618c7ab999968865794',
    'a845ef7236480bd273e338021892f922535958072829'
]

for t in targets:
    print(f"\n=== 搜索: {t} ===")
    # 在所有列中搜索
    found = False
    for col_idx in range(len(df.columns)):
        mask = df.iloc[:, col_idx].astype(str).str.contains(t, na=False)
        if mask.any():
            found = True
            rows = df[mask]
            for i, (idx, row) in enumerate(rows.iterrows()):
                print(f"  在第{col_idx}列找到, 数据行{idx}:")
                for j, v in enumerate(row):
                    print(f"    列{j}: {str(v)[:60]}")
                if i >= 1:
                    break
            break
    if not found:
        print(f"  未找到!")
