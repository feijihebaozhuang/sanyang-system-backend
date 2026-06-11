# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re
from collections import Counter

# ===== 1. 检查定制链接文件中的内容 =====
f = r'D:\Desktop\定制链接商品.xlsx'
df = pd.read_excel(f, skiprows=1, dtype=str)
specs = df['规格名称'].dropna().astype(str).str.strip()

print(f'=== 定制链接共 {len(df)} 条 ===')

# 关键词统计
kw_counter = Counter()
has_keyword = {
    '定制/订制/定做': 0,
    '珍珠棉': 0,
    '咨询客服': 0,
    '不接受退货': 0,
    '万款现货': 0,
    '加工': 0,
    '其他关键词': 0
}

for s in specs:
    if '定制' in s or '订制' in s or '定做' in s:
        has_keyword['定制/订制/定做'] += 1
    elif '珍珠棉' in s:
        has_keyword['珍珠棉'] += 1
    elif '咨询客服' in s:
        has_keyword['咨询客服'] += 1
    elif '不接受退货' in s:
        has_keyword['不接受退货'] += 1
    elif '万款现货' in s:
        has_keyword['万款现货'] += 1
    elif '加工' in s:
        has_keyword['加工'] += 1
    else:
        has_keyword['其他关键词'] += 1

for k, v in has_keyword.items():
    print(f'  {k}: {v}')

# 输出那部分"其他"的看看有没有误判
if has_keyword['其他关键词'] > 0:
    print(f'\n=== 其他关键词的定制链接（可能有误判） ===')
    for s in specs:
        if not any(kw in s for kw in ['定制','订制','定做','珍珠棉','咨询客服','不接受退货','万款现货','加工']):
            print(f'  {s[:80]}')

# ===== 2. 检查普通商品中是否还有含"定制"等关键词的 =====
print(f'\n=== 验证其他文件中是否有遗漏的定制链接 ===')
f2 = r'D:\Desktop\长宽高为整数商品.xlsx'
df2 = pd.read_excel(f2, skiprows=1, dtype=str)
specs2 = df2['规格名称'].dropna().astype(str).str.strip()

missing_custom = []
for s in specs2:
    if any(kw in s for kw in ['定制','订制','定做','珍珠棉','万款现货','定制产品','定制拍单','定做专拍','加工定制']):
        missing_custom.append(s)
        if len(missing_custom) <= 10:
            print(f'  遗漏: {s[:80]}')

print(f'\n其他文件中遗漏的定制链接: {len(missing_custom)} 条')
