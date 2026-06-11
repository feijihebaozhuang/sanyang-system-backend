# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('三羊', na=False)
df2 = df[mask]
print('=== 阿里三羊剩余 %d条 ===\n' % len(df2))

from collections import Counter
cats = Counter()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '外尺寸白色' in s: cats['外尺寸白色(格式①)'] += 1
    elif '外尺寸' in s: cats['外尺寸(格式②)'] += 1
    elif '宽高' in s: cats['宽高(格式③)'] += 1
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
        if len(seen) >= 20:
            break
