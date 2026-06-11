# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)

mask = df['店铺简称'].str.contains('止合', na=False)
zh = df[mask].copy().reset_index(drop=True)
specs = zh['规格名称'].dropna().astype(str).str.strip()

print(f'天猫止合共: {len(zh)} 条\n')

# 归类每种格式 + 展示样例
cats = Counter()
examples = {}
for s in specs:
    # 格式1: 飞机盒【长度Xcm】外径n个一组;层数;【宽度Xcm】X【高度Xcm】
    if '\u98de\u673a\u76d2' in s and '\u957f\u5ea6' in s:
        cats['\u98de\u673a\u76d2\u3010\u957f\u5ea6Xcm\u3011\u5916\u5f84n\u4e2a;\u5c42\u6570;\u3010\u5bbd\u5ea6\u3011X\u3010\u9ad8\u5ea6\u3011'] += 1
    elif '\u5bbd\u3010' in s:
        cats['宽【Xcm】高【Xcm】内径;长【Xcm】'] += 1
    elif '内径' in s:
        cats['内径格式'] += 1
    elif '外径' in s:
        cats['外径格式'] += 1
    else:
        cats[f'其他: {s[:40]}'] += 1

for k, v in cats.most_common(20):
    print(f'  {k}: {v}')

print(f'\n=== 全部规格（{len(specs)}条）===')
for i, s in enumerate(specs):
    print(f'  {i+1}. {s}')
