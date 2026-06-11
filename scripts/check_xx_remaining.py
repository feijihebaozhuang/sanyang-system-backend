# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stdin.reconfigure(encoding='utf-8')
import pandas as pd, re

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))

mask = df['店铺简称'].str.contains('新鑫星', na=False)
df2 = df[mask]

# E类161条
e_items = df2[df2['规格名称'].str.match(r'(长[\d.]+|^[\d.]+)\s*CM[；;]\s*宽', na=False)]
print('=== E类161条 ===')
for _, row in e_items.iterrows():
    s = str(row['规格名称'])
    # 提取尺寸
    m = re.search(r'长?([\d.]+)\s*CM[；;]\s*宽\s*([\d.]+)\s*CM[；;]\s*高度([\d.]+)\s*CM', s)
    if m:
        print('  %s | %s %s %s 外径 特硬' % (s[:60], m.group(1), m.group(2), m.group(3)))

print('\n=== 未分类21条 ===')
unmask = ~df2['规格名称'].str.match(r'(长[\d.]+|^[\d.]+)\s*CM[；;]\s*宽', na=False)
for _, row in df2[unmask].iterrows():
    print('  %s | 规格ID: %s' % (row['规格名称'], row['平台规格id']))
