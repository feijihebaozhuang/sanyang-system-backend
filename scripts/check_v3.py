# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

src = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(src, header=1, dtype=str)
total_raw = len(df)
print(f'原始平台商品: {total_raw} 条')

files = [
    '定制链接商品.xlsx',
    '扣底盒双插盒商品.xlsx',
    '纸箱商品.xlsx',
    '非全量飞机盒.xlsx',
    '其余商品.xlsx',
]

# 先用第一行的中文列名来确认
sample = pd.read_excel(rf'D:\Desktop\{files[0]}')
print(f'\n样本文件列名: {list(sample.columns)}')

# 正确列名
COL_SPEC = '规格名称'
COL_SID = '平台规格id'
COL_SHOP = '店铺名称'
COL_PID = '平台商品id'

total_check = 0
all_ids = set()
dup_count = 0

for fname in files:
    path = rf'D:\Desktop\{fname}'
    df_f = pd.read_excel(path, skiprows=1, dtype=str)
    c = len(df_f)
    total_check += c
    cols = list(df_f.columns)
    
    # 找规格名称列
    spec_col = [c for c in cols if '规格名称' in str(c) or '规格' in str(c)]
    sid_col = [c for c in cols if '规格id' in str(c)]
    shop_col = [c for c in cols if '店铺' in str(c)]
    pid_col = [c for c in cols if '商品id' in str(c)]
    
    spec_col_name = spec_col[0] if spec_col else cols[2]
    sid_col_name = sid_col[0] if sid_col else cols[3]
    shop_col_name = shop_col[0] if shop_col else cols[0]
    pid_col_name = pid_col[0] if pid_col else cols[1]
    
    print(f'\n{fname}:')
    print(f'  条数: {c}')
    print(f'  列: {cols}')
    for _, r in df_f.head(3).iterrows():
        vals = [str(r.get(shop_col_name, ''))[:20], str(r.get(pid_col_name, ''))[:15],
                str(r.get(spec_col_name, ''))[:40], str(r.get(sid_col_name, ''))[:15]]
        print(f'    {vals}')
    
    # 检查规格id重复
    for sid in df_f[sid_col_name].dropna().astype(str).str.strip():
        if sid in all_ids:
            dup_count += 1
        all_ids.add(sid)

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
