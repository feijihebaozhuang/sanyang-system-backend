# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd, re
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('正方形', na=False)
df2 = df[mask]

print('=== 阿里正方形 %d条 ===\n' % len(df2))

# 按格式归类
cats = {}
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    
    # 判断大类
    if '外径' in s and '五层' in s:
        cat = '外径五层纸箱'
    elif '外径' in s and '三层' in s:
        cat = '外径三层纸箱'
    elif '外径' in s and ('E瓦' in s or '特硬' in s):
        cat = '外径E瓦/特硬'
    elif '内径' in s:
        cat = '内径'
    elif '外径' in s:
        cat = '外径(其他)'
    elif '外尺寸' in s:
        cat = '外尺寸'
    elif '内尺寸' in s:
        cat = '内尺寸'
    elif '五层' in s:
        cat = '五层纸箱'
    elif '三层' in s:
        cat = '三层纸箱'
    elif 'E瓦' in s or 'e瓦' in s.lower():
        cat = 'E瓦'
    elif '长' in s and '宽' in s and '高' in s:
        cat = '有长宽高'
    else:
        cat = '其他'
    
    if cat not in cats: cats[cat] = []
    cats[cat].append(s)

for k, v in sorted(cats.items(), key=lambda x: -len(x[1])):
    print('\n=== %s: %d条 ===' % (k, len(v)))
    seen = set()
    for s in v:
        if s not in seen:
            seen.add(s)
            print('  %s' % s)
            if len(seen) >= 20:
                print('  ... 还有%d条' % (len(v) - len(seen)))
                break
