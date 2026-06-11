# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import defaultdict

# ===== 1. 读取 5-剩余商品结构.txt 和 6-不属于定制的60个结构.txt 的结构骨架 =====
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

# ===== 2. 读取原.xlsx =====
source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'
print('读取原.xlsx ...')
df = pd.read_excel(source, skiprows=2, dtype=str)
total = len(df)
print(f'总条数: {total}')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

def clean_num(v):
    v = str(v).strip()
    parts = v.split('.')
    return parts[0] + '.' + ''.join(parts[1:]) if len(parts) > 2 else v

def to_cm(v_str):
    v_str = str(v_str).strip().lower()
    m = re.match(r'([\d.]+)\s*(mm|cm|m|厘米|毫米|米)?', v_str)
    if not m: return None
    v = m.group(1)
    unit = m.group(2) or ''
    try:
        v = float(clean_num(v))
    except:
        return None
    if unit in ('mm', '毫米'):
        v = v / 10.0
    elif unit in ('m', '米'):
        v = v * 100
    return round(v, 2)

def extract_lwh(s):
    l = w = h = None
    m = re.search(r'长[度]?\s*[：:＝=]?\s*([\d.]+(?:\s*(?:cm|mm|m|厘米|毫米|米))?)', s)
    if m: l = to_cm(m.group(1))
    m = re.search(r'宽[度]?\s*[：:＝=]?\s*([\d.]+(?:\s*(?:cm|mm|m|厘米|毫米|米))?)', s)
    if m: w = to_cm(m.group(1))
    m = re.search(r'高[度]?\s*[：:＝=]?\s*([\d.]+(?:\s*(?:cm|mm|m|厘米|毫米|米))?)', s)
    if m: h = to_cm(m.group(1))
    if l and w and h: return (l, w, h)
    m = re.search(r'长宽\s*[【\[]?\s*([\d.]+)\s*[×*xX]\s*([\d.]+)', s)
    if m:
        if not l: l = to_cm(m.group(1))
        if not w: w = to_cm(m.group(2))
        if not h:
            m2 = re.search(r'高[度]?\s*[：:＝=]?\s*([\d.]+(?:\s*(?:cm|mm|m)?))', s)
            if m2: h = to_cm(m2.group(1))
    if not (l and w and h):
        m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*[×*xX]\s*([\d.]+)', s)
        if m:
            vals = sorted([to_cm(m.group(1)), to_cm(m.group(2)), to_cm(m.group(3))], reverse=True)
            l, w, h = vals
    if l and w and h:
        if l > 200 or w > 200 or h > 200: return (None, None, None)
        if l < 0.1 or w < 0.1 or h < 0.1: return (None, None, None)
        return (l, w, h)
    return (None, None, None)

# ===== 3. 只匹配5+6的结构，不排除其他 =====
buckets = defaultdict(list)
matched = 0
not_matched = 0

for idx in range(len(df)):
    row = df.iloc[idx]
    spec = str(row.iloc[5] or '').strip()
    pid = str(row.iloc[8] or '').strip()
    shop = str(row.iloc[1] or '').strip() or '(无名)'
    
    if not spec:
        not_matched += 1
        continue
    
    sk = make_skeleton(spec)
    if sk not in ALLOW_SKELETONS:
        not_matched += 1
        continue
    
    matched += 1
    
    l, w, h = extract_lwh(spec)
    if l is None:
        buckets['未提取尺寸'].append((shop, spec, pid, '', 0, 0, 0))
        continue
    
    is_int = all(v == int(v) for v in [l, w, h])
    is_all5 = all(v % 1 == 0.5 for v in [l, w, h])
    
    # 按你最早说的规则：
    # 外径飞机盒 = 长宽高 3项同时整数，或者是外尺寸外径外
    # 内径飞机盒 = 3项同时.5，或者是内尺寸内径内
    # 非全量 = 除去整数 .5 剩下的
    
    if is_int:
        buckets['外径飞机盒'].append((shop, spec, pid, '外径', l, w, h))
    elif is_all5:
        buckets['内径飞机盒'].append((shop, spec, pid, '内径', l, w, h))
    else:
        buckets['非全量飞机盒'].append((shop, spec, pid, '', l, w, h))

print(f'匹配到(5+6): {matched}, 未匹配: {not_matched}, 合计: {matched+not_matched} (应={total})')
for cat in ['外径飞机盒', '内径飞机盒', '非全量飞机盒', '未提取尺寸']:
    print(f'  {cat}: {len(buckets[cat])} 条')

# ===== 4. 写文件 =====
def write_file(data_list, fpath, title):
    if not data_list:
        print(f'  ⚠ {fpath}: 空')
        return
    groups = {}
    for item in data_list:
        shop, spec, pid = item[0], item[1], item[2]
        sk = make_skeleton(spec)
        key = (shop, sk)
        if key in groups:
            groups[key][2] += 1
        else:
            groups[key] = [spec, pid, 1]
    
    by_shop = defaultdict(list)
    for (shop, sk), (spec, pid, cnt) in groups.items():
        by_shop[shop].append((sk, spec, pid, cnt))
    
    shop_order = sorted(by_shop.keys(), key=lambda sh: sum(v[3] for v in by_shop[sh]), reverse=True)
    total_cnt = len(data_list)
    
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(f'{title}\n')
        f.write(f'结构数: {len(groups)}, 总商品数: {total_cnt}\n\n')
        gidx = 0
        for shop in shop_order:
            items = by_shop[shop]
            items.sort(key=lambda x: -x[3])
            shop_total = sum(v[3] for v in items)
            f.write(f'═══ {shop}（{len(items)} 种格式, 共 {shop_total} 条）═══\n')
            for sk, spec, pid, cnt in items:
                gidx += 1
                f.write(f'[{gidx}] [x{cnt}] 结构: {sk}\n')
                f.write(f'    样例: {spec}\n')
                f.write(f'    pid={pid}\n')
                f.write('\n')
    print(f'  ✅ {fpath}: {len(groups)} 结构, {total_cnt} 条')

outdir = r'D:\Desktop'
write_file(buckets['外径飞机盒'], f'{outdir}\\5a-外径飞机盒.txt', '外径飞机盒（长宽高同时为整数）')
write_file(buckets['内径飞机盒'], f'{outdir}\\5b-内径飞机盒.txt', '内径飞机盒（长宽高同时为.5）')
write_file(buckets['非全量飞机盒'], f'{outdir}\\5c-非全量飞机盒.txt', '非全量飞机盒（除去整数和.5）')
write_file(buckets['未提取尺寸'], f'{outdir}\\5d-未提取尺寸.txt', '未提取到尺寸')

print('\n✅ 全部完成！')
