# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()

# 未分类的细分
cats = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '高' in s and 'cm' in s and '长宽【' in s:
        if '【' + str(re.search(r'(\d+)层', s).group(1) if re.search(r'(\d+)层', s) else '') + '层' in s:
            cats['纸箱(高cm+长宽cm+层)'] += 1
        else:
            cats['高cm+长宽'] += 1
    elif '特硬' in s: cats['特硬未分类'] += 1
    elif '超硬' in s: cats['超硬未分类'] += 1
    elif '白色' in s: cats['白色未分类'] += 1
    elif '黄色' in s: cats['黄色未分类'] += 1
    elif '牛皮色' in s: cats['牛皮色未分类'] += 1
    else: cats['真正未分类'] += 1

print('=== 未分类细分 ===')
for k, v in cats.most_common():
    print(f'  {k}: {v}')

# 纸箱(高cm+长宽cm+层) 样本
print('\n=== 纸箱高cm层 样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '高' in s and 'cm' in s and '长宽【' in s and '层' in s:
        if s not in seen:
            seen.add(s)
            print(f'  {s}')
            if len(seen) >= 10: break

# 特硬未分类样本
print('\n=== 特硬/超硬/白色 未分类 样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '特硬' in s or '超硬' in s or '白色' in s:
        if '【内径尺寸】' not in s and '【内径】' not in s and '外尺寸' not in s and '【长宽】' not in s and '优质牛卡' not in s:
            if not re.search(r'-\d+个[\*x]', s) and '长【' not in s:
                if s not in seen:
                    seen.add(s)
                    print(f'  {s}')
                    if len(seen) >= 15: break

# 真正未分类样本
print('\n=== 真正未分类 样本 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '特硬' not in s and '超硬' not in s and '白色' not in s and '黄色' not in s and '牛皮色' not in s:
        if '【内径尺寸】' not in s and '【内径】' not in s and '外尺寸' not in s and '【长宽】' not in s and '优质牛卡' not in s:
            if not re.search(r'-\d+个[\*x]', s) and '长【' not in s:
                if s not in seen:
                    seen.add(s)
                    print(f'  {s}')
                    if len(seen) >= 10: break
