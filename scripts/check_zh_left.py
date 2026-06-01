# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)
mask_zh = df['店铺简称'].str.contains('止合', na=False)
# moved out already, check original

# 重新读原始来查
f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)

# 如果已经移除了，去平卡看
pk = r'D:\Desktop\换绑输出\平卡_待处理.xlsx'
df_pk = pd.read_excel(pk)
mask = df_pk['店铺简称'].str.contains('止合', na=False)
zh = df_pk[mask].copy().reset_index(drop=True)

print(f'平卡中止合: {len(zh)} 条')
if len(zh) > 0:
    specs = zh['规格名称'].dropna().astype(str).str.strip()
    # show unique patterns (first 30 chars)
    from collections import Counter
    prefixes = Counter()
    for s in specs:
        p = s[:60]
        prefixes[p] += 1
    print('\n=== 去重前60字符模式 ===')
    for p, cnt in prefixes.most_common(50):
        print(f'  [{cnt:>3}] {p}')
