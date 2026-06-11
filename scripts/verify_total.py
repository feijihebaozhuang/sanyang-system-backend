# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

src = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(src, header=1, dtype=str)
total_raw = len(df)
print(f'原始平台商品: {total_raw} 条')

files = [
    ('定制链接商品.xlsx', ['店铺名称','平台商品id','规格名称','平台规格id']),
    ('扣底盒双插盒商品.xlsx', ['店铺名称','平台商品id','规格名称','平台规格id','尺寸类型','长','宽','高']),
    ('纸箱商品.xlsx', ['店铺名称','平台商品id','规格名称','平台规格id','尺寸类型','长','宽','高']),
    ('非全量飞机盒.xlsx', ['店铺名称','平台商品id','规格名称','平台规格id','尺寸类型','长','宽','高']),
    ('其余商品.xlsx', ['店铺名称','平台商品id','规格名称','平台规格id','尺寸类型','长','宽','高']),
]

total_check = 0
for fname, cols in files:
    path = rf'D:\Desktop\{fname}'
    df_f = pd.read_excel(path, skiprows=1, dtype=str)
    c = len(df_f)
    total_check += c
    print(f'  {fname}: {c} 条')

print(f'\n合计: {total_check}')
print(f'原始: {total_raw}')
print(f'差异: {total_check - total_raw}')
if total_check == total_raw:
    print('✅ 总数完全一致！')
else:
    print(f'❌ 相差 {abs(total_check - total_raw)} 条')

# 再检查是否有重复的规格id
if total_check == total_raw:
    all_ids = set()
    dup_count = 0
    for fname, cols in files:
        path = rf'D:\Desktop\{fname}'
        df_f = pd.read_excel(path, skiprows=1, dtype=str)
        for sid in df_f['平台规格id'].dropna().astype(str).str.strip():
            if sid in all_ids:
                dup_count += 1
            all_ids.add(sid)
    print(f'\n跨文件重复规格id: {dup_count} 个')
    print(f'去重后: {len(all_ids)} 个')
