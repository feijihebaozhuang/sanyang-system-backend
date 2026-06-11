# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

OUT_DIR = r'd:\Desktop\换绑输出'
PINGKA = os.path.join(OUT_DIR, '平卡_待处理.xlsx')

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
specs = target['规格名称'].dropna().astype(str).str.strip()

# 看前100条具体内容
print(f'剩余阿里友尚: {len(specs)} 条')
print('\n=== 前100条具体规格 ===')
for i, s in enumerate(specs[:100]):
    print(f'  {i+1}. {s}')

# 检查主要的类别
pat_cnt = Counter()
for s in specs:
    if re.match(r'^\d+个', s):
        pat_cnt['n个开头'] += 1
    elif re.match(r'.+?【\d+个】[\*x]', s):
        pat_cnt['【n个】*'] += 1
    elif re.match(r'.+?\d+个[组/]?[\*x]', s):
        pat_cnt['材料n个*'] += 1
    elif '高度' in s:
        pat_cnt['高度'] += 1
    elif '高' in s and '【' in s:
        pat_cnt['高【】格式'] += 1
    elif '长x宽' in s or '长*宽' in s:
        pat_cnt['长x宽'] += 1
    elif '【' in s and '厘米高' in s:
        pat_cnt['【Hcm高】'] += 1
    elif '【' in s and 'mm高' in s:
        pat_cnt['【Hmm高】'] += 1
    else:
        pat_cnt['其他'] += 1

print('\n=== 类别分布 ===')
for k, v in pat_cnt.most_common():
    print(f'  {k}: {v}')
