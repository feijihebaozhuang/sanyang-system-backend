# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

OUT_DIR = r'd:\Desktop\换绑输出'
files = os.listdir(OUT_DIR)
pingka_file = [f for f in files if f.startswith('\u5e73') and f.endswith('.xlsx')][0]
PINGKA = os.path.join(OUT_DIR, pingka_file)

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
samples = target['规格名称'].dropna().astype(str).str.strip().tolist()

print(f'剩余: {len(samples)} 条\n')

# 分类所有模式
categories = Counter()
# 收集每类的示例
examples = {}

for s in samples:
    cat = '其他'
    if re.fullmatch(r'\d+', s): cat = '纯数字'
    elif re.match(r'^\d+个', s): cat = 'n个开头'
    elif re.match(r'^(\d+(?:\.\d+)?)\s*cm高【', s): cat = 'Hcm高【纸箱】前导'
    elif re.match(r'^高(\d+)cm【', s): cat = '高Hcm【层】前导'
    elif re.match(r'^高【(\d+)cm】', s): cat = '高【Hcm】【层】前导'
    elif re.match(r'^高度(\d+)cm【', s): cat = '高度Hcm【纸箱】前导'
    elif re.match(r'^(\d+)x', s): cat = 'LxW前导'
    elif re.match(r'^(\d+)\*(\d+)\*(\d+)', s): cat = 'L*W*H前导'
    elif '【' in s and '个】' in s: cat = '包含【个】'
    elif s.startswith('长x宽') or s.startswith('长*宽'): cat = '长x宽前导'
    elif s.startswith('长度'): cat = '长度前导'
    elif s.startswith('特价'): cat = '特价前导'
    elif '外径' in s or '内径' in s: cat = '内外径含'
    elif '高【' in s: cat = '含高【】'
    elif s.startswith('【'): cat = '【前导'
    else: cat = '其他'
    
    categories[cat] += 1
    if cat not in examples:
        examples[cat] = s[:80]

for k, v in categories.most_common():
    print(f'  {k}: {v}')
    if k in examples:
        print(f'    eg: {examples[k]}')

print('\n=== 全部前80条具体 ===')
for i, s in enumerate(samples[:80]):
    print(f'  {i+1}. {s}')
