# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()

# 格式② 材料分布
mats = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【内径尺寸】' in s:
        m = __import__('re').search(r'^([^-]+)-', s)
        if m:
            mats[m.group(1)] += 1

print('=== 格式②(【内径尺寸】)材料分布 ===')
for k, v in mats.most_common():
    print('  %s: %d条' % (k, v))

# 格式③ 材料分布
mats3 = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【内径】' in s:
        m = __import__('re').search(r'^([^【]+)', s)
        if m:
            mats3[m.group(1).strip()] += 1

print('\n=== 格式③(【内径】)材料分布 ===')
for k, v in mats3.most_common():
    print('  %s: %d条' % (k, v))

# 格式④ 材料分布
mats4 = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '外尺寸' in s or '外径' in s:
        m = __import__('re').search(r'^([^-]+)-外', s)
        if m:
            mats4[m.group(1).strip()] += 1
        else:
            m2 = __import__('re').search(r'^(.+?)外尺寸', s)
            if m2:
                mats4[m2.group(1).strip()] += 1

print('\n=== 格式④(外尺寸/外径)材料分布 ===')
for k, v in mats4.most_common():
    print('  %s: %d条' % (k, v))

# 格式⑤ 纸箱类类型分布
mats5 = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【长宽】' in s:
        m = __import__('re').search(r'【(.+?)】\s*\d+个', s)
        if m:
            mats5[m.group(1)] += 1
        # 也看看前面有没有材料提示
        m2 = __import__('re').search(r'\d+x\d+ cm【长宽】', s)

print('\n=== 格式⑤(纸箱类)类型分布 ===')
for k, v in mats5.most_common():
    print('  %s: %d条' % (k, v))

# 格式⑥ 材料分布
mats6 = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '-100个*' in s or '-50个*' in s:
        m = __import__('re').search(r'^([^-]+)-', s)
        if m:
            mats6[m.group(1)] += 1

print('\n=== 格式⑥(xxx-数量*)材料分布 ===')
for k, v in mats6.most_common():
    print('  %s: %d条' % (k, v))
