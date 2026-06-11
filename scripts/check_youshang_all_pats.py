# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

OUT_DIR = r'd:\Desktop\换绑输出'
PINGKA = os.path.join(OUT_DIR, '平卡_待处理.xlsx')

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
specs = target['规格名称'].dropna().astype(str).str.strip()

# 打印所有种类（按模式归类）
patterns = Counter()
for s in specs:
    if re.search(r'高(\d+)cm【\d+层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】\s*\d+个', s):
        patterns['高Hcm【n层】；长宽【L*W】n个'] += 1
    elif re.search(r'高(\d+)cm【\d+层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】', s):
        patterns['高Hcm【n层】；长宽【L*W】'] += 1
    elif re.search(r'高度(\d+)cm【.+?纸箱】\s*\d+个[^；;]*[；;]长宽([\d.]+)x([\d.]+)(mm|cm)', s):
        patterns['高度Hcm【纸箱】长宽LxWmm/cm'] += 1
    elif re.search(r'高度(\d+)cm【.+?纸箱】\s*\d+个[^；;]*[；;]', s):
        patterns['高度Hcm【纸箱】其他'] += 1
    elif re.search(r'【(\d+)厘米高】(.+?)-(\d+)个[^；;]*[；;]', s):
        patterns['【Hcm高】材料-数量;L*W'] += 1
    elif re.search(r'(.+?)-(\d+)个【(\d+)厘米高】[^；;]*[；;]', s):
        patterns['材料-数量【Hcm高】;L*W'] += 1
    elif re.search(r'(.+?)(\d+)个【(\d+)mm高】[^；;]*[；;]', s):
        patterns['材料n个【Hmm高】;L*W'] += 1
    elif re.search(r'(.+?)\s+(\d+)个【(\d+)厘米高】[^；;]*[；;]', s):
        patterns['材料 n个【Hcm高】;L*W'] += 1
    elif re.search(r'(.+?)【(\d+)个】[\*x]', s):
        patterns['材料【n个】*LxWxH'] += 1
    elif re.search(r'(\d+)个(.+?)[\*x]', s):
        patterns['n个材料*LxWxH'] += 1
    elif re.search(r'长度(\d+)cm---', s):
        patterns['长度Hcm---格式'] += 1
    elif '特价' in s and '一组' in s:
        patterns['特价一组格式'] += 1
    elif re.search(r'(\d+\.\d+|\d+)\*(\d+\.\d+|\d+)\*(\d+\.\d+|\d+)cm\s*外径', s):
        patterns['L*W*Hcm外径格式'] += 1
    elif '长x宽' in s:
        patterns['长x宽格式'] += 1
    elif '高【' in s:
        patterns['高【Hcm】【层纸箱】格式'] += 1
    else:
        patterns['其他:' + s[:30]] += 1

print(f'剩余阿里友尚: {len(specs)} 条\n')
print('=== 格式分布 ===')
for k, v in patterns.most_common(50):
    print(f'  {k}: {v}')

print('\n=== 所有未归类的前20条 ===')
i = 0
for s in specs:
    if not re.search(r'高\d+cm|高度\d+|【\d+厘米高】|【\d+个】\*|\d+个.+?\*|长度\d+|---|特价|外径|长x宽', s):
        print(f'  {s}')
        i += 1
        if i >= 20: break
