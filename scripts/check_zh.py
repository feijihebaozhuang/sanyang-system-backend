# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)

mask = df['店铺简称'].str.contains('止合', na=False)
zh = df[mask].copy()
print(f'天猫止合共: {len(zh)} 条\n')

# 看规格名称分布
specs = zh['规格名称'].dropna().astype(str).str.strip()
from collections import Counter
cnt = Counter()
for s in specs:
    # 归类
    if s.startswith('宽【') or s.startswith('宽【'):
        cnt['宽【cm】高【cm】内径;长【cm】'] += 1
    elif '宽' in s and '高' in s and '长' in s:
        cnt['宽/高/长 格式'] += 1
    elif '内径' in s:
        cnt['内径格式'] += 1
    else:
        cnt[f'其他: {s[:30]}'] += 1

print('=== 格式分布 ===')
for k, v in cnt.most_common(20):
    print(f'  {k}: {v}')

print('\n=== 前20条具体规格 ===')
for i, s in enumerate(specs[:20]):
    print(f'  {i+1}. {s}')

print('\n=== 尝试解析 ===')
print(f'  前5条尝试解析列:')
for _, r in zh.head(5).iterrows():
    print(f'    {str(r.get("尝试解析",""))[:50]}')
