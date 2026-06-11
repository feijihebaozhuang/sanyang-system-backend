# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('三羊', na=False)
df2 = df[mask].copy()

print('=== 三羊格式A: 外尺寸材料【H cm高】（分号在外尺寸前） ===\n')
mat_counter = Counter()
h_counter = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '外尺寸' not in s:
        continue
    # 提取材料
    m = __import__('re').search(r'外尺寸([^【;]*?)【', s)
    if m:
        mat = m.group(1).strip() or '无色'
        mat_counter[mat] += 1
    # 提取高度
    m2 = __import__('re').search(r'【\s*([\d.]+)\s*cm高】', s)
    if m2:
        h_counter[m2.group(1)] += 1

print('  材料分布:')
for k, v in mat_counter.most_common():
    print('    %s: %d条' % (k or '空白', v))

print('\n  继续看194条无【】的:')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【' not in s and s not in seen:
        seen.add(s)
        print('    %s' % s)
