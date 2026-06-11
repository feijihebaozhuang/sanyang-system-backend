# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re

src = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(src, header=1, dtype=str)
total_raw = len(df)
print(f'原始平台商品: {total_raw} 条')

files = [
    ('定制链接商品.xlsx', ['店铺名称','平台商品id','规格名称','平台规格id']),
    ('扣底盒双插盒商品.xlsx', None),
    ('纸箱商品.xlsx', None),
    ('非全量飞机盒.xlsx', None),
    ('其余商品.xlsx', None),
]

total_check = 0
all_ids = set()
dup_count = 0
issues = []

for fname, _ in files:
    path = rf'D:\Desktop\{fname}'
    df_f = pd.read_excel(path, skiprows=1, dtype=str)
    c = len(df_f)
    total_check += c
    cols = list(df_f.columns)
    print(f'\n{fname}:')
    print(f'  条数: {c}')
    print(f'  列: {cols}')
    print(f'  前3行:')
    for _, r in df_f.head(3).iterrows():
        vals = [str(r.get(c, ''))[:40] for c in cols[:4]]
        print(f'    {vals}')
    
    # 检查规格id重复
    for sid in df_f['平台规格id'].dropna().astype(str).str.strip():
        if sid in all_ids:
            dup_count += 1
            if dup_count <= 3:
                issues.append(f'重复sid: {sid}')
        all_ids.add(sid)
    
    # 检查是否有空的规格名称
    empty_specs = df_f['规格名称'].isna().sum()
    if empty_specs > 0:
        issues.append(f'  ⚠️ 空规格名称: {empty_specs}条')

print(f'\n\n=== 总数验证 ===')
print(f'合计: {total_check}')
print(f'原始: {total_raw}')
if total_check == total_raw:
    print('✅ 总数一致')
else:
    print(f'❌ 相差 {abs(total_check - total_raw)}')

print(f'\n去重规格id: {len(all_ids)}')
print(f'跨文件重复: {dup_count}')

if dup_count == 0:
    print('✅ 无重复')
else:
    print(f'⚠️ 有{dup_count}个重复')

if issues:
    print(f'\n⚠️ 问题:')
    for i in issues:
        print(f'  {i}')
else:
    print('✅ 无其他问题')

print(f'\n=== 各文件条数摘要 ===')
for fname, _ in files:
    path = rf'D:\Desktop\{fname}'
    df_f = pd.read_excel(path, skiprows=1, dtype=str)
    print(f'{fname}: {len(df_f)}')
