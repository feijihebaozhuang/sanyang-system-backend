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

# ===== 1. 5+6 的所有骨架 =====
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

# ===== 2. 从原.xlsx 找出所有含"红"且骨架在5+6中的 =====
custom_items = []
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

print(f'含"红"商品: {len(custom_items)} 条')
print(f'含"红"结构: {len(custom_skeletons_seen)} 个')

# ===== 3. 同时也读取之前1a中 13个黑&红结构 所在的骨架 =====
# 这些结构在之前的 remove_custom_from_5_update_1a.py 中已经从5里移走了
# 所以它们不在 current 5+6 中，我们需要从之前的 1a 中保留
old_1a_red_skeletons = set()
old_1a_items = []
with open(r'D:\Desktop\1a-定制商品结构（补充）.txt', 'r', encoding='utf-8') as f:
    for line in f:
        m = re.match(r'\s*\[\d+\]\s*\[x\d+\]\s*结构:\s*(.+)', line)
        if m:
            sk = m.group(1).strip()
            if '黑&红' in sk:
                old_1a_red_skeletons.add(sk)

# 从原.xlsx 中取回这些结构的全部数据
old_1a_seen = set()
for idx in range(len(df)):
    row = df.iloc[idx]
    spec = str(row.iloc[5] or '').strip()
    pid = str(row.iloc[8] or '').strip()
    shop = str(row.iloc[1] or '').strip() or '(无名)'
    if not spec:
        continue
    sk = make_skeleton(spec)
    if sk in old_1a_red_skeletons:
        old_1a_items.append((shop, spec, pid, sk))

print(f'旧1a黑&红结构: {len(old_1a_red_skeletons)}')
print(f'旧1a黑&红商品数（重从原.xlsx读）: {len(old_1a_items)}')

# ===== 4. 合并新旧 =====
all_items = custom_items + old_1a_items
all_skeletons = set()
for _, _, _, sk in all_items:
    all_skeletons.add(sk)

# ===== 5. 写 1a =====
by_shop = defaultdict(list)
seen = set()
for shop, spec, pid, sk in all_items:
    key = (shop, sk)
    if key not in seen:
        seen.add(key)
        by_shop[shop].append((sk, spec, pid, 0))

struct_count = defaultdict(int)
for shop, spec, pid, sk in all_items:
    struct_count[(shop, sk)] += 1

shop_order = sorted(by_shop.keys(), key=lambda sh: sum(struct_count[(sh, sk)] for sk, _, _, _ in by_shop[sh]), reverse=True)

gidx = 0
total_cnt = len(all_items)
total_structs = len(all_skeletons)

outpath = r'D:\Desktop\1a-定制商品结构（补充）.txt'

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

print(f'✅ 写入 1a: {total_structs} 结构, {total_cnt} 条')
print(f'   （其中黑&红: {len(old_1a_red_skeletons)} 结构, 新增红: {len(custom_skeletons_seen)} 结构）')
