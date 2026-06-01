# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

# 重新从原始无匹配读（如果备份还在的话 - 用git恢复）
# 或者直接看换绑文件第40批的内容
okdir = r'D:\Desktop\换绑输出\OK文件'
f40 = os.path.join(okdir, '换绑文件_第40批.xlsx')
if os.path.exists(f40):
    df = pd.read_excel(f40, skiprows=1)
    print(f'第40批: {len(df)} 条')
    codes = df['商品编码'].tolist()
    print('前5个编码:')
    for c in codes[:5]:
        print(f'  {c}')

# 看这些商品编码对应的快麦数据，验证合理性
# 另外，看一下无匹配中筛选出来的336条无匹配（已被移到了平卡? 不对，是从无匹配删除的）
# 重新检查无匹配是否还有止合（因为v3从无匹配中移除了）
nm = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df_nm = pd.read_excel(nm)
mask = df_nm['店铺简称'].str.contains('止合', na=False)
print(f'\n无匹配剩余止合: {df_nm[mask].shape[0]} 条（应为0）')

# 看看之前被标记为"无匹配"的336条
# 它们的平台规格id已被移除了，所以只能用spec_name再匹配一次
# 改用平卡（原本的原始数据）
pk = r'D:\Desktop\换绑输出\平卡_待处理.xlsx'
df_pk = pd.read_excel(pk)
mask_pk = df_pk['店铺简称'].str.contains('止合', na=False)
print(f'\n平卡中止合: {df_pk[mask_pk].shape[0]} 条')

# 如果平卡也没有，说明batch_zh_v3已经把平卡里的止合标记移除了但之前统计说只有13匹配
# 看看那336条无匹配+770条未识别是不是已经被移到了无匹配但又被删了？
specs = df_nm['规格名称'].dropna().astype(str).str.strip()
# 看有没有标志性止合格式
counts = Counter()
for s in specs:
    if '飞机盒' in s:
        counts['飞机盒'] += 1
    if '扣底盒' in s:
        counts['扣底盒'] += 1
    if '纸箱' in s:
        counts['纸箱'] += 1
    if '信封' in s:
        counts['信封'] += 1
    if 'A4纸' in s:
        counts['A4纸'] += 1
    if 'E坑' in s:
        counts['E坑'] += 1
print(f'\n无匹配中剩余各类型（不区分店铺）:')
for k, v in counts.most_common():
    print(f'  {k}: {v}')
