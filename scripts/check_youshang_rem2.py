# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'
PINGKA = os.path.join(OUT_DIR, '平卡_待处理.xlsx')

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
specs = target['规格名称'].dropna().astype(str).str.strip()

from collections import Counter
cnt = Counter()
for s in specs:
    if '高度' in s:
        cnt['高度'] += 1
    elif '高【' in s or '高 ' in s or '高\t'in s:
        cnt['高【/高x格式'] += 1
    elif '【' in s and '个' in s and ('*' in s or 'x' in s):
        cnt['【n个】*LxWxH格式'] += 1
    elif re.search(r'\d+个', s) and ('*' in s or 'x' in s):
        cnt['n个*LxWxH直接格式'] += 1
    elif '长宽' in s:
        cnt['长宽'] += 1
    elif '长x宽' in s or '长*宽' in s:
        cnt['长x宽格式'] += 1
    elif '【' in s and '厘米高' in s:
        cnt['【Hcm高】格式'] += 1
    elif '外径' in s or '内径' in s:
        cnt['内外径格式'] += 1
    elif '特价' in s:
        cnt['特价格式'] += 1
    elif '长度' in s:
        cnt['长度格式'] += 1
    else:
        cnt['其他'] += 1

print(f'剩余阿里友尚: {len(specs)} 条\n')
print('=== 格式分布 ===')
for k, v in cnt.most_common():
    print(f'  {k}: {v}')

print('\n=== 前80条具体规格 ===')
for i, s in enumerate(specs[:80]):
    print(f'  {i+1}. {s}')
