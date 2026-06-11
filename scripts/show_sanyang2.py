# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('三羊', na=False)
df2 = df[mask].copy()

# 看其他和无内外径的
cats = {
    '外尺寸白色': [],
    '外尺寸牛皮色': [],
    '外尺寸黄色': [],
    '外尺寸': [],
    '无外尺寸': [],
}
from collections import Counter
other_cats = Counter()

for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '外尺寸白色' in s: cats['外尺寸白色'].append(s)
    elif '外尺寸牛皮色' in s: cats['外尺寸牛皮色'].append(s)
    elif '外尺寸黄色' in s: cats['外尺寸黄色'].append(s)
    elif '外尺寸' in s: cats['外尺寸'].append(s)
    else:
        # 其他格式细分
        if '【' in s:
            other_cats['有【】'] += 1
            if '内径' in s: other_cats['内径'] += 1
            elif '外径' in s: other_cats['外径'] += 1
            elif '高度' in s or '高' in s: other_cats['有高度'] += 1
            else: other_cats['其他有【】'] += 1
        else:
            other_cats['无【】'] += 1

print('=== 主格式 ===')
for k, v in cats.items():
    print('  %s: %d条' % (k, len(v)))

print('\n=== 其他格式 ===')
for k, v in other_cats.most_common():
    print('  %s: %d条' % (k, v))

print('\n=== 非外尺寸白色抽样 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '外尺寸白色' in s: continue
    if s not in seen:
        seen.add(s)
        print('  %s' % s)
        if len(seen) >= 30:
            break
