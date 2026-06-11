# -*- coding: utf-8 -*-
"""
直接从平台商品.xlsx整站分类，分批处理
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re

src = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(src, header=1, dtype=str)

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
    m = re.search(r'(?:外[尺寸]*寸*[大小]*|内[尺寸]*寸*[大小]*)[：:]?\s*【\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*】\s*(cm|mm|c|m)?', s)
    if m:
        l = normalize_dim(m.group(1)+(m.group(4) or '')); w = normalize_dim(m.group(2)+(m.group(4) or '')); h = normalize_dim(m.group(3)+(m.group(4) or ''))
        if l and w and h and 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
    m = re.search(r'【\s*长\s*([\d.]+)\s*[xX*×]\s*宽\s*([\d.]+)\s*[xX*×]\s*高\s*([\d.]+)\s*】', s)
    if m:
        l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
    m = re.search(r'长[度]*[：:]?\s*【\s*([\d.]+)\s*(cm|mm|c|m)?\s*】.*?宽[度]*[：:]?\s*【\s*([\d.]+)\s*(cm|mm|c|m)?\s*】.*?高[度]*[：:]?\s*【\s*([\d.]+)\s*(cm|mm|c|m)?\s*】', s)
    if m:
        l = normalize_dim(m.group(1)+(m.group(2) or '')); w = normalize_dim(m.group(3)+(m.group(4) or '')); h = normalize_dim(m.group(5)+(m.group(6) or ''))
        if l and w and h and 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
    m = re.search(r'【\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*[xX*×]\s*([\d.]+)\s*】\s*(cm|mm|c|m)?', s)
    if m:
        l = normalize_dim(m.group(1)+(m.group(4) or '')); w = normalize_dim(m.group(2)+(m.group(4) or '')); h = normalize_dim(m.group(3)+(m.group(4) or ''))
        if l and w and h and 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
    m = re.search(r'(?<![\d.])([\d.]+)\s*[xX*]\s*([\d.]+)\s*[xX*]\s*([\d.]+)\s*(cm|mm|c|m)?(?![\d.])', s)
    if m:
        l = normalize_dim(m.group(1)+(m.group(4) or '')); w = normalize_dim(m.group(2)+(m.group(4) or '')); h = normalize_dim(m.group(3)+(m.group(4) or ''))
        if l and w and h and 0 < l <= 300 and 0 < w <= 300 and 0 < h <= 300: return (l, w, h)
    return None

def is_dot5(v):
    return v != int(v) and abs(v * 2 - round(v * 2)) < 0.01

def classify_dim(s):
    lwh = extract_lwh(s)
    if not lwh: return None
    l, w, h = lwh
    if all(abs(n - round(n)) < 0.001 for n in (l, w, h)):
        return ('整数', int(round(l)), int(round(w)), int(round(h)))
    elif all(is_dot5(n) for n in (l, w, h)):
        return ('全5', l, w, h)
    else:
        return ('小数', l, w, h)

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

OUT_COLS = ['店铺名称','平台商品id','平台规格名称','平台规格id','尺寸类型','长','宽','高']

# 先收集所有行到列表
custom_list = []; kd_list = []; zx_list = []; other_list = []

total = len(df)
for idx, (_, row) in enumerate(df.iterrows()):
    s = str(row.get('平台规格名称', '')).strip()
    if not s: continue
    if is_custom(s):
        custom_list.append(row); continue
    dim = classify_dim(s)
    if dim:
        row['尺寸类型'] = dim[0]; row['长'] = dim[1]; row['宽'] = dim[2]; row['高'] = dim[3]
    else:
        row['尺寸类型'] = ''; row['长'] = ''; row['宽'] = ''; row['高'] = ''
    if '扣底盒' in s or '扣抵盒' in s or '双插盒' in s:
        kd_list.append(row)
    elif '纸箱' in s:
        zx_list.append(row)
    else:
        other_list.append(row)
    
    if (idx+1) % 50000 == 0:
        print(f'  已处理 {idx+1}/{total}...')

# 从other_list中分非全量飞机盒
feiji_rows = []; remaining_other = []
for row in other_list:
    s = str(row.get('平台规格名称', '')).strip()
    dim = classify_dim(s)
    if dim and dim[0] == '小数':
        feiji_rows.append(row)
    else:
        remaining_other.append(row)

print(f'\n结果: 定制={len(custom_list)} 扣底盒={len(kd_list)} 纸箱={len(zx_list)} 非全量飞机盒={len(feiji_rows)} 其余={len(remaining_other)}')
print(f'合计: {len(custom_list)+len(kd_list)+len(zx_list)+len(feiji_rows)+len(remaining_other)} = {total}')

import openpyxl as opx

def save_xlsx(path, data, title):
    rows = []
    for row in data:
        shop = str(row.get('店铺名称','')).strip()
        pid = str(row.get('平台商品id','')).strip()
        spec = str(row.get('平台规格名称','')).strip()
        sid = str(row.get('平台规格id','')).strip()
        dt = str(row.get('尺寸类型',''))
        l = row.get('长',''); w = row.get('宽',''); h = row.get('高','')
        rows.append([shop, pid, spec, sid, dt, l, w, h])
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

save_xlsx(r'D:\Desktop\定制链接商品.xlsx', custom_list, '定制链接（无准确尺寸）')
save_xlsx(r'D:\Desktop\扣底盒双插盒商品.xlsx', kd_list, '扣底盒/双插盒')
save_xlsx(r'D:\Desktop\纸箱商品.xlsx', zx_list, '纸箱')
save_xlsx(r'D:\Desktop\非全量飞机盒.xlsx', feiji_rows, '其余商品中带小数点的（非全.5）- 非全量飞机盒')
save_xlsx(r'D:\Desktop\其余商品.xlsx', remaining_other, '其余商品（已移除小数项）')
print('\n✅ 全部文件已生成到桌面！')
