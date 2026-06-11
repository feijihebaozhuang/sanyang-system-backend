# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import defaultdict

source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'
print('读取原.xlsx ...')
df = pd.read_excel(source, skiprows=2, dtype=str)

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

def has_red(s):
    return '红' in s

# ===== 1. 读 5+6 允许的骨架 =====
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
print(f'5+6 结构总数: {len(ALLOW_SKELETONS)}')

# ===== 2. 从原.xlsx 找出所有含"红"的 =====
# 先收集所有含"红"且骨架在 5+6 中的行
custom_items = []  # (shop, spec, pid)
custom_skeletons_seen = set()

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
        custom_items.append((shop, spec, pid, sk))
        custom_skeletons_seen.add(sk)

print(f'5+6 中含"红"商品: {len(custom_items)} 条')
print(f'5+6 中含"红"结构: {len(custom_skeletons_seen)} 个')

# ===== 3. 追加到 1a-定制商品结构（补充）.txt =====
# 按shop分组
by_shop = defaultdict(list)
seen_for_dedup = set()
new_items = []
for shop, spec, pid, sk in custom_items:
    key = (shop, sk)
    if key not in seen_for_dedup:
        seen_for_dedup.add(key)
        by_shop[shop].append((sk, spec, pid, 0))
    # 统计该结构在 new_items 中的条数(先收集再计数)
    new_items.append((shop, spec, pid, sk))

# 统计每个结构的条数
struct_count = defaultdict(int)
for shop, spec, pid, sk in new_items:
    struct_count[(shop, sk)] += 1

shop_order = sorted(by_shop.keys(), key=lambda sh: sum(struct_count[(sh, sk)] for sk, _, _, _ in by_shop[sh]), reverse=True)

gidx = 0
total_cnt = len(new_items)
total_structs = len(seen_for_dedup)

outpath = r'D:\Desktop\1a-定制商品结构（补充）.txt'

with open(outpath, 'r', encoding='utf-8') as f:
    existing = f.read()

with open(outpath, 'w', encoding='utf-8') as f:
    f.write('定制商品结构（补充—从5和6中挑出）\n')
    f.write(f'结构数: {total_structs}, 总商品数: {total_cnt}\n\n')
    
    for shop in shop_order:
        items = by_shop[shop]
        items.sort(key=lambda x: -struct_count[(shop, x[0])])
        shop_total = sum(struct_count[(shop, sk)] for sk, _, _, _ in items)
        f.write(f'═══ {shop}（{len(items)} 种格式, 共 {shop_total} 条）═══\n')
        for sk, spec, pid, _ in items:
            gidx += 1
            cnt = struct_count[(shop, sk)]
            f.write(f'[{gidx}] [x{cnt}] 结构: {sk}\n')
            f.write(f'    样例: {spec}\n')
            f.write(f'    pid={pid}\n')
            f.write('\n')

print(f'✅ 1a-定制商品结构（补充）.txt 已更新')
print(f'   结构数: {total_structs}, 商品数: {total_cnt}')
