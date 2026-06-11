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

# 分类
cnt = Counter()
for s in samples:
    cat = '其他'
    if re.match(r'^(\d+)\s*cm高【', s): cat = 'Hcm高【纸箱前导'
    elif '高【' in s and '层' in s: cat = '高【Hcm】层格式'
    elif re.match(r'^\d+个', s): cat = 'n个开头'
    elif '超级' in s: cat = '超级开头'
    elif '长*宽' in s: cat = '长*宽格式'
    elif '长度' in s: cat = '长度格式'
    elif '【' in s and '个' in s and ('*' in s or 'x' in s): cat = '包含【n个】*格式'
    elif s.startswith('高') or s.startswith('高【'): cat = '高开头格式'
    elif 'cm' in s: cat = '含cm格式'
    elif s.startswith('长x宽'): cat = '长x宽格式'
    else: cat = '其他'
    cnt[cat] += 1

for k, v in cnt.most_common():
    print(f'  {k}: {v}')

print('\n=== 全部前80条 ===')
for i, s in enumerate(samples[:80]):
    print(f'  {i+1}. {s}')
