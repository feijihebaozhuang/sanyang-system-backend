# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
print('平卡总数: %d\n' % len(df))
print('=== 店铺分布 ===')
for k, v in Counter(df['店铺简称'].dropna()).most_common():
    print('  %s: %d条' % (k, v))

print('\n=== 抽样 ===')
for _, row in df.head(10).iterrows():
    print('  [%s] %s' % (row['店铺简称'], str(row['规格名称'])[:80]))
