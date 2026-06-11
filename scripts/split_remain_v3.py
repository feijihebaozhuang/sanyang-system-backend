# -*- coding: utf-8 -*-
"""
从 原.xlsx 读取全部数据。
排除已分类的结构pid，剩余商品提取长宽高，分3类。
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

# ===== 1. 收集已分类结构的pid =====
EXCLUDED_PIDS = set()
files_to_exclude = [
    r'D:\Desktop\1-定制商品结构.txt',
    r'D:\Desktop\2-扣底盒商品结构.txt',
    r'D:\Desktop\3-双插盒商品结构.txt',
    r'D:\Desktop\4-三层纸箱商品结构.txt',
    r'D:\Desktop\4a-五层纸箱商品结构.txt',
    r'D:\Desktop\6-不属于定制的60个结构.txt',
]
for fpath in files_to_exclude:
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\s*pid=(.+)', line)
            if m:
                EXCLUDED_PIDS.add(m.group(1).strip())

print(f'已分类的pid数: {len(EXCLUDED_PIDS)}')

# ===== 2. 读取 =====
source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'
print('用pandas读取原.xlsx ...')
df = pd.read_excel(source, skiprows=2, dtype=str)
print(f'shape: {df.shape}')
print(f'总条数: {len(df)}')

# 列: 0=平台, 1=店铺名称, 2=商品id, 3=商品名, 4=(空), 5=规格名称, 6=(空), 7=(空), 8=规格id, 9=链接
# 确定店铺名和规格名称的列
shop_col = 1
spec_col = 5
pid_col = 8

shop_vals = df.iloc[:, shop_col].astype(str).str.strip()
spec_vals = df.iloc[:, spec_col].astype(str).str.strip()
pid_vals = df.iloc[:, pid_col].astype(str).str.strip()

# ===== 3. 过滤已分类 =====
remain_mask = ~pid_vals.isin(EXCLUDED_PIDS)
remain_df = df[remain_mask]
print(f'未分类商品: {len(remain_df)} 条')
print(f'已分类商品: {len(df) - len(remain_df)} 条')

# ===== 4. 提取长宽高 =====
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
            vals = [to_cm(m.group(1)), to_cm(m.group(2)), to_cm(m.group(3))]
            # 按大小排序确定长宽高（不一定有序）
            vals.sort(reverse=True)
            l, w, h = vals
    
    if not (l and w and h):
        m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*cm?\s*【长宽】', s)
        if m:
            l = to_cm(m.group(1))
            w = to_cm(m.group(2))
            m2 = re.search(r'高度?\s*([\d.]+)\s*cm', s)
            if m2: h = to_cm(m2.group(1))
    
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

# ===== 5. 分类 =====
from collections import defaultdict
class_buckets = defaultdict(list)

for idx in range(len(remain_df)):
    row = remain_df.iloc[idx]
    s = str(row.iloc[spec_col] or '').strip()
    shop = str(row.iloc[shop_col] or '').strip() or '(无名)'
    pid = str(row.iloc[pid_col] or '').strip()
    
    if not s:
        class_buckets['未提取尺寸'].append((shop, s, pid, None, None, None, None))
        continue
    
    l, w, h = extract_lwh(s)
    if l is None:
        class_buckets['未提取尺寸'].append((shop, s, pid, None, None, None, None))
        continue
    
    is_wai = is_waijing(s)
    dim_type = '外径' if is_wai else '内径'
    
    is_int = all(v == int(v) for v in [l, w, h])
    is_all5 = all(v % 1 == 0.5 for v in [l, w, h])
    
    if is_int:
        class_buckets['外径飞机盒(整数)'].append((shop, s, pid, dim_type, l, w, h))
    elif is_all5:
        class_buckets['内径飞机盒(.5)'].append((shop, s, pid, dim_type, l, w, h))
    else:
        class_buckets['非全量飞机盒(其他小数)'].append((shop, s, pid, dim_type, l, w, h))

for cat in ['外径飞机盒(整数)', '内径飞机盒(.5)', '非全量飞机盒(其他小数)', '未提取尺寸']:
    items = class_buckets[cat]
    print(f'{cat}: {len(items)} 条')

total_check = sum(len(v) for v in class_buckets.values())
print(f'合计: {total_check} 条 (应={len(remain_df)})')
if total_check == len(remain_df):
    print('✅ 数量正确！')
else:
    print(f'❌ 差 {abs(total_check - len(remain_df))}')

# ===== 6. 写文件 =====
def skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

def write_file(data_list, fpath, title):
    groups = {}
    for item in data_list:
        shop = item[0]
        spec = item[1]
        pid = item[2]
        sk = skeleton(spec)
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
write_file(class_buckets['外径飞机盒(整数)'], f'{outdir}\\5a-外径飞机盒.txt', '外径飞机盒（长宽高同时为整数）')
write_file(class_buckets['内径飞机盒(.5)'], f'{outdir}\\5b-内径飞机盒.txt', '内径飞机盒（长宽高同时为.5，或明确内径）')
write_file(class_buckets['非全量飞机盒(其他小数)'], f'{outdir}\\5c-非全量飞机盒.txt', '非全量飞机盒（其他小数）')
write_file(class_buckets['未提取尺寸'], f'{outdir}\\5d-未提取尺寸.txt', '未提取到尺寸')

print('\n✅ 全部完成！')
