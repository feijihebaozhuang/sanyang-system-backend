# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()

# 输出所有不同的规格名
seen = set()
seen2 = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    # 转为简单表示
    simple = re.sub(r'\d+\.\d+', 'X.X', s)
    simple = re.sub(r'\d+', 'N', s)
    # 去重
    if simple not in seen2:
        seen2.add(simple)
        seen.add(s)

all_unique = list(seen)
print(f'共 {len(df2)} 条, {len(seen)} 种不同规格\n')
print('=== 全部不同规格 ===')
for i, s in enumerate(sorted(seen)):
    print(f'{i+1}. {s}')
