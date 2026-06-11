# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('三羊', na=False)
df2 = df[mask].copy()

print('=== 阿里三羊 共%d条 ===\n' % len(df2))

# 先看看最常见的格式分类
from collections import Counter
cats = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【' in s:
        if '内径' in s: cats['含内径'] += 1
        elif '外径' in s: cats['含外径'] += 1
        elif '外尺寸' in s: cats['外尺寸'] += 1
        else: cats['有【】但无内外径'] += 1
    elif '外径' in s: cats['外径无【】'] += 1
    elif '内径' in s: cats['内径无【】'] += 1
    else: cats['其他'] += 1

for k, v in cats.most_common():
    print('  %s: %d条' % (k, v))

print('\n=== 抽样规格 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if s not in seen:
        seen.add(s)
        print('  %s' % s)
        if len(seen) >= 40:
            break
