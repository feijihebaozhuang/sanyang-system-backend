# -*- coding: utf-8 -*-
"""
直接从原始平台商品.xlsx做非全量飞机盒
逻辑：排除 定制链接 + 扣底盒/双插盒 + 纸箱，剩下的其余商品中
取出带小数点的（排除全.5）→ 非全量飞机盒.xlsx
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re

src = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(src, header=1, dtype=str)
print(f'原始: {len(df)} 条')

def normalize_dim(v_str):
    v_str = v_str.strip()
    unit = ''; val_str = v_str
    if v_str.lower().endswith('cm'): unit = 'cm'; val_str = v_str[:-2].strip()
    elif v_str.lower().endswith('mm'): unit = 'mm'; val_str = v_str[:-2].strip()
    elif v_str.lower().endswith('c'): unit = 'cm'; val_str = v_str[:-1].strip()
    elif v_str.lower().endswith('m'): unit = 'mm'; val_str = v_str[:-1].strip()
    try:
        v = float(val_str)
        return v / 10 if unit == 'mm' else v
    except: return None

def extract_lwh(s):
    s = str(s)
    # 外尺寸【LxWxH】
    m = re.search(r'(?:外[尺寸]*寸*[大小]*|内[尺寸]*寸*[大小]*)[：:]?\s*【\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*】\s*(cm|mm|c|m)?', s)
    if m:
        l = normalize_dim(m.group(1)+(m.group(4) or '')); w = normalize_dim(m.group(2)+(m.group(4) or '')); h = normalize_dim(m.group(3)+(m.group(4) or ''))
        if l and w and h and 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
    # 【长Lx宽Wx高H】
    m = re.search(r'【\s*长\s*([\d.]+)\s*[xX*×]\s*宽\s*([\d.]+)\s*[xX*×]\s*高\s*([\d.]+)\s*】', s)
    if m:
        l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
    # 长【L】宽【W】高【H】
    m = re.search(r'长[度]*[：:]?\s*【\s*([\d.]+)\s*(cm|mm|c|m)?\s*】.*?宽[度]*[：:]?\s*【\s*([\d.]+)\s*(cm|mm|c|m)?\s*】.*?高[度]*[：:]?\s*【\s*([\d.]+)\s*(cm|mm|c|m)?\s*】', s)
    if m:
        l = normalize_dim(m.group(1)+(m.group(2) or '')); w = normalize_dim(m.group(3)+(m.group(4) or '')); h = normalize_dim(m.group(5)+(m.group(6) or ''))
        if l and w and h and 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
    # 【LxWxH】
    m = re.search(r'【\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*】\s*(cm|mm|c|m)?', s)
    if m:
        l = normalize_dim(m.group(1)+(m.group(4) or '')); w = normalize_dim(m.group(2)+(m.group(4) or '')); h = normalize_dim(m.group(3)+(m.group(4) or ''))
        if l and w and h and 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
    # LxWxH 在分号后或行末（主要格式！如 "【100个】;51.5*25.5*4.5"）
    m = re.search(r'(?:[；;]\s*|^)(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*$', s)
    if m:
        try:
            l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
            if 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
        except: pass
    # 任意位置 LxWxH 前后不是数字
    m = re.search(r'(?<!\d)(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)\s*[xX*]\s*(\d+\.?\d*)(?!\d)', s)
    if m:
        try:
            l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
            if 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
        except: pass
    return None

def is_dot5(v):
    return v != int(v) and abs(v * 2 - round(v * 2)) < 0.01

def is_custom(s):
    if re.search(r'[\d.]+\s*[xX*×]\s*[\d.]+\s*[xX*×]\s*[\d.]+', s): return False
    if re.search(r'【\s*[\d.]+', s): return False
    if re.search(r'[长宽高][度]*\s*[：:]?\s*【\s*[\d.]+', s): return False
    for kw in ['定制','订制','定做','加工定制','不接受退货','咨询客服','拍下联系客服',
               '定制产品','定制拍单','定制尺寸','万款现货','联系客服备注','详情咨询',
               '更多尺寸','下拉查看','1000款现模','更多尺寸看详情','详情-现模']:
        if kw in s: return True
    if '珍珠棉' in s: return True
    if len(re.findall(r'[\d.]+', s)) == 0: return True
    return False

feiji = []
other_remain = []
total_other = 0

for idx, (_, row) in enumerate(df.iterrows()):
    s = str(row.get('平台规格名称', '')).strip()
    if not s: continue
    
    # 排除定制、扣底盒、双插盒、纸箱
    if is_custom(s): continue
    if '扣底盒' in s or '扣抵盒' in s or '双插盒' in s: continue
    if '纸箱' in s: continue
    
    total_other += 1
    lwh = extract_lwh(s)
    if not lwh:
        other_remain.append(row)
        continue
    l, w, h = lwh
    has_dot = any(n != int(n) for n in (l, w, h))
    all_dot5 = all(is_dot5(n) for n in (l, w, h))
    if has_dot and not all_dot5:
        feiji.append(row)
    else:
        other_remain.append(row)
    
    if (idx+1) % 50000 == 0:
        print(f'  已处理 {idx+1}/{len(df)}...')

print(f'\n其余商品总计: {total_other}')
print(f'非全量飞机盒(带小数非全.5): {len(feiji)} 条')
print(f'其余商品剩余: {len(other_remain)} 条')

import openpyxl as opx

OUT_COLS = ['店铺名称','平台商品id','平台规格名称','平台规格id','尺寸类型','长','宽','高']

def save(path, data, title):
    rows = []
    for row in data:
        shop = str(row.get('店铺名称','')).strip()
        pid = str(row.get('平台商品id','')).strip()
        spec = str(row.get('平台规格名称','')).strip()
        sid = str(row.get('平台规格id','')).strip()
        rows.append([shop, pid, spec, sid, '', '', '', ''])
    pd.DataFrame(rows, columns=OUT_COLS).to_excel(path, index=False)
    wb = opx.load_workbook(path)
    ws = wb.active
    ws.insert_rows(1); ws.cell(1, 2).value = title
    ws.column_dimensions['C'].width = 60
    for c in ['E','F','G','H']:
        try: ws.column_dimensions[c].width = 10
        except: pass
    wb.save(path)
    print(f'  ✅ {os.path.basename(path)}: {len(rows)}条')

save(r'D:\Desktop\非全量飞机盒.xlsx', feiji, '其余商品中带小数点的（已排除全.5）- 非全量飞机盒')
save(r'D:\Desktop\其余商品.xlsx', other_remain, '其余商品（已移除小数项）')

print(f'\n验证: 256+7266+33214+{len(feiji)}+{len(other_remain)} = {256+7266+33214+len(feiji)+len(other_remain)}')
