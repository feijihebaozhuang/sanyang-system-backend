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

# ===== 2. 从原.xlsx 找出骨架在 5+6 中且含"红"的 =====
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

print(f'含"红"商品: {len(items)} 条')
print(f'含"红"结构: {len(skeletons)} 个')

# ===== 3. 那13个"黑&红"结构在以前运行 remove_custom_from_5_update_1a.py 时被从5移到了1a
# 它们已经不在当前的5+6里了。为了找到它们，我们从原.xlsx 中直接搜
# 这些结构的特征：骨架包含 黑&红
for idx in range(len(df)):
    row = df.iloc[idx]
    spec = str(row.iloc[5] or '').strip()
    pid = str(row.iloc[8] or '').strip()
    shop = str(row.iloc[1] or '').strip() or '(无名)'
    if not spec:
        continue
    sk = make_skeleton(spec)
    # 骨架是否包含"黑&红"（可能被N替换后变成类似 "双面纯色【N个】黑&红;N*N*N" 的样子）
    if '黑&红' in sk or '黑和红' in sk:
        if sk not in skeletons:  # 还没加过
            items.append((shop, spec, pid, sk))
            skeletons.add(sk)

print(f'加上黑&红后: {len(items)} 条, {len(skeletons)} 个结构')

# ===== 4. 按店分组，写1a =====
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

gidx = 0
total_cnt = len(items)
total_structs = len(skeletons)

outpath = r'D:\Desktop\1a-定制商品结构（补充）.txt'

with open(outpath, 'w', encoding='utf-8') as f:
    f.write('定制商品结构（补充—从5和6中挑出）\n')
    f.write(f'结构数: {total_structs}, 总商品数: {total_cnt}\n\n')
    
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

print(f'✅ 写入完成: {total_structs} 结构, {total_cnt} 条')
