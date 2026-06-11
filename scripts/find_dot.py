# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re

f = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(f, header=1, dtype=str)
print(f'列名: {list(df.columns)}')
print(f'总行: {len(df)}')

specs = df['平台规格名称'].dropna().astype(str).str.strip()

# 提取所有长宽高数字（含小数点的）
def extract_dims(s):
    nums = re.findall(r'(\d+\.?\d*)', s)
    return [float(n) for n in nums if float(n) > 0]

count_dot = 0
count_all_dot5 = 0

rows_with_dot = []
for idx, s in enumerate(specs):
    nums = extract_dims(s)
    if len(nums) < 3: continue
    
    # 看哪些包含小数点
    has_dot = any(n != int(n) for n in nums)
    if has_dot:
        count_dot += 1
        # 检查长宽高中是否同时为.5
        # 找长宽高的数字部分
        dims = []
        # 提取【长33.5】或【33.5*22.5】这类格式中的数字
        m_dims = re.findall(r'【[\d.*xX]+?】', s)
        for dm in m_dims:
            ns = re.findall(r'(\d+\.?\d*)', dm)
            dims.extend([float(n) for n in ns if float(n) > 0])
        
        if len(dims) >= 3:
            major = dims[:3]  # 取前3个作为长宽高
            all_dot5 = all(abs(n - round(n)) < 0.01 and n != int(n) and n * 2 % 1 == 0 for n in major)
            if all_dot5:
                count_all_dot5 += 1
            else:
                rows_with_dot.append(idx)

print(f'\n包含小数点的规格: {count_dot}')
print(f'长宽高同时为.5: {count_all_dot5}')
print(f'有小数但不是全.5: {len(rows_with_dot)}')

# 输出样本
print(f'\n=== 样本（有小数非全.5）===')
for idx in rows_with_dot[:20]:
    s = specs.iloc[idx]
    nums = re.findall(r'(\d+\.?\d*)', s)
    print(f'  {s[:60]} → {[float(n) for n in nums if float(n) > 0][:6]}')
