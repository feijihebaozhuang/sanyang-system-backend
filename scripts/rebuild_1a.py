# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import defaultdict

source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'
print('读取原.xlsx ...')
df = pd.read_excel(source, skiprows=2, dtype=str)
print(f'总行: {len(df)}')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

def has_red(s):
    return '红' in s

# 5+6 骨架
ALLOW_SKELETONS = set()
for fpath in [
    r'D:\Desktop\5-剩余商品结构.txt',
    r'D:\Desktop\6-不属于定制的60个结构.txt',
]:
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\s*\[\d+\]\s*\[x\d+\]\s*结构:\s*(.+)', line)
            if m:
                ALLOW_SKELETONS.add(m.group(1).strip())

# 一次遍历原.xlsx，收集所有骨架在5+6中且含"红"的
items = []
skeletons = set()

for idx in range(len(df)):
    row = df.iloc[idx]
    spec = str(row.iloc[5] or '').strip()
    pid = str(row.iloc[8] or '').strip()
    shop = str(row.iloc[1] or '').strip() or '(无名)'
    if not spec:
        continue
    sk = make_skeleton(spec)
    if sk not in ALLOW_SKELETONS:
        continue
    if has_red(spec):
        items.append((shop, spec, pid, sk))
        skeletons.add(sk)

print(f'5+6中含"红": {len(items)} 条, {len(skeletons)} 结构')

# 也找包含"黑&红"的（即使不在5+6里，因为它们之前被移到了1a）
for idx in range(len(df)):
    row = df.iloc[idx]
    spec = str(row.iloc[5] or '').strip()
    pid = str(row.iloc[8] or '').strip()
    shop = str(row.iloc[1] or '').strip() or '(无名)'
    if not spec:
        continue
    sk = make_skeleton(spec)
    if sk in skeletons:
        continue
    if '黑&红' in sk or '黑和红' in sk:
        items.append((shop, spec, pid, sk))
        skeletons.add(sk)

print(f'加上黑&红后: {len(items)} 条, {len(skeletons)} 结构')

# 写文件
by_shop = defaultdict(list)
seen = set()
for shop, spec, pid, sk in items:
    key = (shop, sk)
    if key not in seen:
        seen.add(key)
        by_shop[shop].append((sk, spec, pid, 0))

struct_count = defaultdict(int)
for shop, spec, pid, sk in items:
    struct_count[(shop, sk)] += 1

shop_order = sorted(by_shop.keys(), key=lambda sh: sum(struct_count[(sh, sk)] for sk, _, _, _ in by_shop[sh]), reverse=True)

outpath = r'D:\Desktop\1a-定制商品结构（补充）.txt'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write('定制商品结构（补充—从5和6中挑出）\n')
    f.write(f'结构数: {len(skeletons)}, 总商品数: {len(items)}\n\n')
    gidx = 0
    for shop in shop_order:
        lst = by_shop[shop]
        lst.sort(key=lambda x: -struct_count[(shop, x[0])])
        shop_total = sum(struct_count[(shop, sk)] for sk, _, _, _ in lst)
        f.write(f'═══ {shop}（{len(lst)} 种格式, 共 {shop_total} 条）═══\n')
        for sk, spec, pid, _ in lst:
            gidx += 1
            cnt = struct_count[(shop, sk)]
            f.write(f'[{gidx}] [x{cnt}] 结构: {sk}\n')
            f.write(f'    样例: {spec}\n')
            f.write(f'    pid={pid}\n')
            f.write('\n')

print(f'✅ 1a: {len(skeletons)} 结构, {len(items)} 条')
