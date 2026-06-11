# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()

# 细分"其他"中的格式
cats = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '优质牛卡' in s: cats['优质牛卡'] += 1
    elif '双白' in s: cats['双白-内径mm'] += 1
    elif '【内径尺寸】' in s: cats['有【内径尺寸】'] += 1
    elif '内径' in s: cats['内径'] += 1
    elif '外径' in s or '外尺寸' in s: cats['外径/外尺寸'] += 1
    elif '特硬' in s: cats['特硬'] += 1
    elif '超硬' in s: cats['超硬'] += 1
    elif '白色' in s: cats['白色'] += 1
    elif '黄色' in s: cats['黄色'] += 1
    elif '牛皮色' in s: cats['牛皮色'] += 1
    elif 'x' in s or '*' in s:
        if '【' in s: cats['有【】x格式'] += 1
        else: cats['x格式无【】'] += 1
    elif '*' in s: cats['*格式'] += 1
    else: cats['其他'] += 1

print('=== 细分 ===')
for k, v in cats.most_common():
    print('  %s: %d条' % (k, v))

# 抽样显示每个类别
print('\n=== 各分类抽样 ===')
for cat_name in ['双白-内径mm', '有【内径尺寸】', '内径', '外径/外尺寸', '有【】x格式', 'x格式无【】', '其他']:
    cnt = 0
    seen = set()
    for _, row in df2.iterrows():
        s = str(row['规格名称'])
        match = False
        if cat_name == '双白-内径mm': match = '双白' in s
        elif cat_name == '有【内径尺寸】': match = '【内径尺寸】' in s and '双白' not in s
        elif cat_name == '内径': match = '内径' in s and '双白' not in s and '【内径尺寸】' not in s
        elif cat_name == '外径/外尺寸': match = '外径' in s or '外尺寸' in s
        elif cat_name == '有【】x格式': match = ('x' in s or '*' in s) and '【' in s and '优质' not in s and '双白' not in s and '内径' not in s and '外径' not in s and '外尺寸' not in s and '特硬' not in s and '超硬' not in s and '白色' not in s
        elif cat_name == 'x格式无【】': match = ('x' in s or '*' in s) and '【' not in s and '双白' not in s and '内径' not in s and '外径' not in s
        elif cat_name == '其他':
            if '优质' not in s and '双白' not in s and '内径' not in s and '外径' not in s and '外尺寸' not in s and '特硬' not in s and '超硬' not in s and '白色' not in s and '黄色' not in s and '牛皮色' not in s and 'x' not in s and '*' not in s:
                match = True
        if match and s not in seen:
            seen.add(s)
            print('  [%s] %s' % (cat_name, s))
            cnt += 1
            if cnt >= 3:
                break
