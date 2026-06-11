# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(os.path.join(out, '平卡_待处理.xlsx'))
mask = df['店铺简称'].str.contains('新鑫星', na=False)
df2 = df[mask]

# E类
e_items = df2[df2['规格名称'].str.match(r'长?[\d.]+', na=False)]
print('=== E类 %d条 ===' % len(e_items))

# 列出所有需要匹配的尺寸（外径、内径转后）
import re
codes_needed = set()
codes_inner = set()
for _, row in e_items.iterrows():
    s = str(row['规格名称'])
    m = re.search(r'长?([\d.]+)\s*CM[；;]\s*宽\s*([\d.]+)\s*CM[；;]\s*高度([\d.]+)\s*CM', s)
    if m:
        l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
        # 外径
        dims = sorted([l, w, h], reverse=True)
        codes_needed.add(f"{dims[0]:g}*{dims[1]:g}*{dims[2]:g}-外径-特硬")
        # 内径
        il, iw, ih = dims[0]-1.5, dims[1]-0.5, dims[2]-0.5
        if il > 0:
            codes_needed.add(f"{il:g}*{iw:g}*{ih:g}-内径-特硬")

# 加载快麦
km_file = r'd:\Desktop\快麦商品 - 副本.xlsx'
km = pd.read_excel(km_file, sheet_name='报表1', header=3, dtype=str, usecols=[0,1,2])
km_codes = set()
for row in km.values:
    code = str(row[0] or '').strip()
    if code: km_codes.add(code)

print('\n=== 快麦里能匹配到的 ===')
matched = set()
for code in sorted(codes_needed):
    if code in km_codes:
        matched.add(code)

for code in sorted(matched):
    print('  ✅ %s' % code)

print('\n=== 匹配不到的（抽样30条） ===')
unmatched = codes_needed - matched
cnt = 0
for code in sorted(unmatched):
    if cnt < 30:
        print('  ❌ %s' % code)
    cnt += 1
if cnt > 30:
    print('  ... 还有%d条' % (cnt - 30))

# 看看快麦里相近的都有什么
print('\n=== 快麦里相近代码（包含特硬） ===')
import re as re2
close = [c for c in km_codes if '特硬' in c and re2.search(r'\d+\*', c)]
print('  包含"特硬"的编码共%d条' % len(close))
# 统计外径/内径分布
dk_count = Counter()
for c in close:
    parts = c.split('-')
    if len(parts) >= 2:
        dk_count[parts[1]] += 1
    else:
        dk_count['未知'] += 1
print(' 内外径分布:', dict(dk_count))
# 尺寸范围
dims_list = []
for c in close:
    d = c.split('-')[0]
    if d and d[0].isdigit():
        ds = d.split('*')
        if len(ds)==3:
            try: dims_list.append(tuple(float(x) for x in ds))
            except: pass
if dims_list:
    print('  尺寸范围: 长%.1f~%.1f 宽%.1f~%.1f 高%.1f~%.1f' % (
        min(d[0] for d in dims_list), max(d[0] for d in dims_list),
        min(d[1] for d in dims_list), max(d[1] for d in dims_list),
        min(d[2] for d in dims_list), max(d[2] for d in dims_list),
    ))
