# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'
files = os.listdir(OUT_DIR)
pingka_file = [f for f in files if f.startswith('\u5e73') and f.endswith('.xlsx')][0]
PINGKA = os.path.join(OUT_DIR, pingka_file)

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
samples = target['规格名称'].dropna().astype(str).str.strip().tolist()

# 看"其他"和"内外径含"类的具体情况
from collections import Counter
ohter_samples = Counter()
other_examples = {}

for s in samples:
    if '超级超级硬' in s:
        ohter_samples['超级超级硬'] += 1
        if '超级超级硬' not in other_examples:
            other_examples['超级超级硬'] = s[:80]
    elif '超级硬' in s:
        ohter_samples['超级硬'] += 1
        if '超级硬' not in other_examples:
            other_examples['超级硬'] = s[:80]
    elif '超硬黄色100个' in s and '*' not in s and 'x' not in s:
        ohter_samples['超硬黄色100个无星'] += 1
    elif s.startswith('长*宽'):
        ohter_samples['长*宽ns;n个高度Hmm[材料]'] += 1
        if '长*宽' not in other_examples:
            other_examples['长*宽'] = s[:80]
    elif s.startswith('长度'):
        ohter_samples['长度Hcm--材料-n个组'] += 1
        if '长度' not in other_examples:
            other_examples['长度'] = s[:80]
    elif s.startswith('【9长系列】'):
        ohter_samples['【9长系列】'] += 1
    elif 'mm高' in s and '长宽' in s and not re.search(r'\*\d', s):
        ohter_samples['mm高;长宽LxW'] += 1
        if 'mm高' not in other_examples:
            other_examples['mm高'] = s[:80]
    elif '【' in s and '个】' in s and '*' not in s and 'x' not in s:
        ohter_samples['【n个】无星'] += 1
    else:
        # 无法分类的
        ohter_samples['其他未分类'] += 1
        if '其他未分类' not in other_examples:
            other_examples['其他未分类'] = s[:80]

print('剩余格式分布:')
for k, v in ohter_samples.most_common():
    print(f'  {k}: {v}')
    if k in other_examples:
        print(f'    e.g. {other_examples[k]}')

# 打印所有无法分类的
print('\n=== 无法分类的样例（前20） ===')
cnt = 0
for s in samples:
    if not re.search(r'超级|高度|长\*宽|长度|【9长|mm高.*长宽|【.*个】|特价|cm高【', s):
        print(f'  {s[:80]}')
        cnt += 1
        if cnt >= 20: break
