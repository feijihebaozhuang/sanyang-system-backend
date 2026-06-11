# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()
print(f'剩余 {len(df2)} 条\n')

# 用关键词细分
cats = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【内径尺寸】' in s: cats['内径尺寸mm'] += 1
    elif '【内径】' in s: cats['内径在中间'] += 1
    elif '【外径】' in s: cats['外径直接'] += 1
    elif '外尺寸' in s: cats['外尺寸'] += 1
    elif '【长宽】' in s: cats['有长宽关键词'] += 1
    elif '优质牛卡' in s: cats['优质牛卡'] += 1
    elif re.search(r'-\d+个[\*x]', s): cats['直接格式'] += 1
    elif '长【' in s: cats['长L宽W'] += 1
    elif '24cm高度' in s: cats['24cm定制'] += 1
    elif '长' in s and 'mm' in s and '宽高' in s: cats['mm宽高'] += 1
    elif '高' in s and '长宽' in s: cats['高+长宽'] += 1
    elif '长度' in s: cats['长度'] += 1
    else: cats['其他'] += 1

# fix typo
del cats['内径在中间']
cats['【内径】'] = sum(1 for _, row in df2.iterrows() if '【内径】' in str(row['规格名称']))

for k, v in cats.most_common():
    print(f'  {k}: {v}')

# 看看"其他"的
print('\n=== 其他 样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    known = bool(re.search(r'【内径尺寸】|【内径】|【外径】|外尺寸|【长宽】|优质牛卡|-\d+个[\*x]|长【|24cm高度|mm.*宽高', s))
    if not known and s not in seen:
        seen.add(s)
        print(f'  {s}')
        if len(seen) >= 25: break

# 也看看内径尺寸mm中的前几个不匹配的是啥
print('\n=== 内径尺寸mm 典型样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【内径尺寸】' in s:
        if s not in seen:
            seen.add(s)
            print(f'  {s}')
            if len(seen) >= 5: break
