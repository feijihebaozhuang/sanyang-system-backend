# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(f, header=1, dtype=str)
specs = df['平台规格名称'].dropna().astype(str).str.strip()

# 看看定制链接和珍珠棉的特征
custom = specs[specs.str.contains('定制|珍珠棉|咨询客服', na=False)]
print(f'定制类/珍珠棉: {len(custom)} 条')

print('\n=== 前20条 ===')
for s in custom.head(20):
    print(f'  {s[:80]}')

print('\n=== 去重前60字符 ===')
from collections import Counter
pref = Counter()
for s in custom:
    pre = s[:60]
    # 去掉数字部分，只看文字特征
    import re
    text_only = re.sub(r'[\d.]+', '', pre)
    pref[text_only] += 1
for p, c in pref.most_common(20):
    print(f'  [{c:>4}] {p}')
