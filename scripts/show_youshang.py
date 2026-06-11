# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()

print('=== 阿里友尚 共%d条 ===\n' % len(df2))

# 快速分类
cats = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '优质牛卡' in s: cats['优质牛卡'] += 1
    elif '特硬' in s: cats['特硬'] += 1
    elif '超硬' in s: cats['超硬'] += 1
    elif '白色' in s: cats['白色'] += 1
    elif '牛皮色' in s: cats['牛皮色'] += 1
    elif '黄色' in s: cats['黄色'] += 1
    elif 'E瓦' in s or 'E瓦' in s: cats['E瓦'] += 1
    elif 'B坑' in s: cats['B坑'] += 1
    else: cats['其他'] += 1

for k, v in cats.most_common():
    print('  %s: %d条' % (k, v))

print('\n=== 抽样 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if s not in seen:
        seen.add(s)
        print('  %s' % s)
        if len(seen) >= 30:
            break
