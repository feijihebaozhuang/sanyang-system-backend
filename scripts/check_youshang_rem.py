# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'
PINGKA = os.path.join(OUT_DIR, '平卡_待处理.xlsx')

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
specs = target['规格名称'].dropna().astype(str).str.strip()

from collections import Counter
cnt = Counter()
for s in specs:
    # 归类
    if re.search(r'【(\d+)厘米高】', s):
        if '长宽' in s:
            cnt['[Hcm高]材料-数量;L*W[长宽]'] += 1
        elif 'mm' in s or 'CM' in s:
            cnt['[Hcm高]材料-数量;L*W单位'] += 1
        else: cnt['[Hcm高]-其他'] += 1
    elif re.search(r'【(\d+)mm高】', s):
        cnt['[Hmm高]格式'] += 1
    elif re.search(r'\d+mm高', s):
        cnt['mm高长宽格式'] += 1
    elif re.search(r'\d+cm高', s):
        cnt['cm高长宽格式'] += 1
    elif re.search(r'\d+个.+?\*', s):
        cnt['数量前导*格式'] += 1
    elif re.search(r'.*?【\d+个】\*', s):
        cnt['【数量】*格式'] += 1
    elif re.search(r'\d+\.\d+\*\d+\.\d+\*\d+\.\d+', s):
        cnt['直接L*W*H格式'] += 1
    elif re.search(r'\d+x\s*\d+', s):
        cnt['x分隔长宽格式'] += 1
    elif re.search(r'特价\s+\d+', s):
        cnt['特价一组格式'] += 1
    elif re.search(r'外径|外寸|内径|内寸', s):
        cnt['内外径格式'] += 1
    elif '长度' in s and '--' in s:
        cnt['长度Ncm--格式'] += 1
    elif '高度' in s or '高【' in s:
        cnt['高度/高【格式'] += 1
    else:
        cnt['其他'] += 1

print(f'剩余阿里友尚: {len(specs)} 条\n')
print('=== 格式分布 ===')
for k, v in cnt.most_common():
    print(f'  {k}: {v}')

# 打印前50条具体内容
print('\n=== 前50条具体规格 ===')
for i, s in enumerate(specs[:50]):
    print(f'  {i+1}. {s}')
