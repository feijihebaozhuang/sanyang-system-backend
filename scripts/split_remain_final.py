# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import defaultdict

# ===== 1. 读取5-剩余商品结构.txt的所有结构骨架 =====
REMAIN_SKELETONS = set()
with open(r'D:\Desktop\5-剩余商品结构.txt', 'r', encoding='utf-8') as f:
    for line in f:
        m = re.match(r'\s*\[\d+\]\s*\[x\d+\]\s*结构:\s*(.+)', line)
        if m:
            sk = m.group(1).strip()
            # 去空格（骨架本身已经去空格了）
            REMAIN_SKELETONS.add(sk)
print(f'剩余结构数: {len(REMAIN_SKELETONS)}')

# ===== 2. 读取原.xlsx =====
source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'
print('读取原.xlsx ...')
df = pd.read_excel(source, skiprows=2, dtype=str)
total = len(df)
print(f'总条数: {total}')

def make_skeleton(s):
    s = re.sub(r'\d+\.?\d*', 'N', s)
    s = re.sub(r'\s+', '', s)
    return s[:300]

def clean_num(v):
    v = str(v).strip()
    parts = v.split('.')
    if len(parts) > 2:
        return parts[0] + '.' + ''.join(parts[1:])
    return v

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
    
    if l and w and h:
        return (l, w, h)
    
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
        if l > 200 or w > 200 or h > 200:
            return (None, None, None)
        if l < 0.1 or w < 0.1 or h < 0.1:
            return (None, None, None)
        return (l, w, h)
    return (None, None, None)

def is_waijing(s):
    if '内径' in s or '内尺寸' in s:
        if '外径' in s or '外尺寸' in s:
            return True
        return False
    return True

# 排除的pid：1/2/3/4/4a 所有结构的pid
EXCLUDED_PIDS = set()
for fpath in [
    r'D:\Desktop\1-定制商品结构.txt',
    r'D:\Desktop\2-扣底盒商品结构.txt',
    r'D:\Desktop\3-双插盒商品结构.txt',
    r'D:\Desktop\4-三层纸箱商品结构.txt',
    r'D:\Desktop\4a-五层纸箱商品结构.txt',
]:
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\s*pid=(.+)', line)
            if m:
                EXCLUDED_PIDS.add(m.group(1).strip())

print(f'排除pid数: {len(EXCLUDED_PIDS)}')

# ===== 3. 匹配并分类 =====
buckets = defaultdict(list)
matched = 0
not_matched = 0
excluded = 0

for idx in range(len(df)):
    row = df.iloc[idx]
    spec = str(row.iloc[5] or '').strip()
    pid = str(row.iloc[8] or '').strip()
    shop = str(row.iloc[1] or '').strip() or '(无名)'
    
    # 先排除已分类
    if pid in EXCLUDED_PIDS:
        excluded += 1
        continue
    
    # 骨架匹配
    if not spec:
        not_matched += 1
        continue
    
    sk = make_skeleton(spec)
    if sk not in REMAIN_SKELETONS:
        not_matched += 1
        continue
    
    matched += 1
    
    # 提取尺寸
    l, w, h = extract_lwh(spec)
    if l is None:
        buckets['未提取尺寸'].append((shop, spec, pid, '', 0, 0, 0))
        continue
    
    is_wai = is_waijing(spec)
    dt = '外径' if is_wai else '内径'
    is_int = all(v == int(v) for v in [l, w, h])
    is_all5 = all(v % 1 == 0.5 for v in [l, w, h])
    
    if is_int:
        buckets['外径飞机盒'].append((shop, spec, pid, dt, l, w, h))
    elif is_all5:
        buckets['内径飞机盒'].append((shop, spec, pid, dt, l, w, h))
    else:
        buckets['非全量飞机盒'].append((shop, spec, pid, dt, l, w, h))

print(f'\n排除(1/2/3/4/4a): {excluded}')
print(f'匹配到剩余结构: {matched}')
print(f'未匹配: {not_matched}')
print(f'合计: {excluded+matched+not_matched} (应={total})')

for cat in ['外径飞机盒', '内径飞机盒', '非全量飞机盒', '未提取尺寸']:
    print(f'{cat}: {len(buckets[cat])} 条')

# ===== 4. 写文件 =====
def write_file(data_list, fpath, title):
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
write_file(buckets['外径飞机盒'], f'{outdir}\\5a-外径飞机盒.txt', '外径飞机盒（长宽高同时为整数，沉默外径）')
write_file(buckets['内径飞机盒'], f'{outdir}\\5b-内径飞机盒.txt', '内径飞机盒（长宽高同时为.5，或明确内径）')
write_file(buckets['非全量飞机盒'], f'{outdir}\\5c-非全量飞机盒.txt', '非全量飞机盒（其他小数）')
write_file(buckets['未提取尺寸'], f'{outdir}\\5d-未提取尺寸.txt', '未提取到尺寸')

print('\n✅ 全部完成！')
