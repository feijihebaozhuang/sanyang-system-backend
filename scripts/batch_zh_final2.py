# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'D:\Desktop\换绑输出'
nm_path = os.path.join(OUT_DIR, '无匹配_待处理.xlsx')

km = pd.read_excel(r'D:\Desktop\快麦商品 - 副本.xlsx', sheet_name='报表1', header=3, dtype=str, usecols=[0])
all_codes = set()
for row in km.values:
    code = str(row[0] or '').strip()
    if code: all_codes.add(code)

fuzzy_idx = {}
for code in all_codes:
    parts = code.split('-')
    if len(parts) >= 3:
        dims = parts[0].split('*')
        if len(dims) == 3:
            try:
                vals = tuple(sorted([float(d) for d in dims]))
                dk = parts[1]
                mat = '-'.join(parts[2:])
                fk = (vals[0], vals[1], vals[2], dk)
                fuzzy_idx.setdefault(fk, []).append((code, mat))
            except: pass

def dfmt(v):
    s = f'{v:.1f}'
    return s.rstrip('0').rstrip('.')

def match_3d(l, w, h, dk, mat):
    code = f'{l}*{w}*{h}-{dk}-{mat}'
    if code in all_codes: return code
    code2 = f'{w}*{l}*{h}-{dk}-{mat}'
    if code2 in all_codes: return code2
    try:
        vals = tuple(sorted([float(l), float(w), float(h)]))
        fk = (vals[0], vals[1], vals[2], dk)
        candidates = fuzzy_idx.get(fk, [])
        for c, cm in candidates:
            if mat in cm or cm in mat or cm == mat: return c
        if candidates: return candidates[0][0]
    except: pass
    return None

def parse_zh(s):
    s = s.strip()
    
    # 1. 飞机盒【长度Lcm】外径n个一组;3层;【宽度Wcm】X【高度Hcm】
    m = re.search(r'飞机盒【长度(\d+)CM】外径\d+个一组[^；;]*[；;]\d+层[^；;]*[；;]【宽度(\d+)CM】\s*X\s*【高度(\d+)CM】', s, re.I)
    if m: return ('特硬', sorted([int(m.group(1)), int(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # 2. 飞机盒【长度Lcm】【材料】;3层;【宽度Wcm】X【高度Hcm】
    m = re.search(r'飞机盒【长度(\d+)CM】【[^】]+】[^；;]*[；;]\d+层[^；;]*[；;]【宽度(\d+)CM】\s*X\s*【高度(\d+)CM】', s, re.I)
    if m: return ('特硬', sorted([int(m.group(1)), int(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # 3. 5级进口特硬-/宽*高【W*Hcm】;3层;飞机盒长度【Lcm】/n个一捆;特硬【颜色】
    m = re.search(r'/宽\*高【([\d.]+)\*([\d.]+)cm】[^；;]*[；;]\d+层[^；;]*[；;]飞机盒长度【(\d+)cm】', s)
    if m:
        w, h, l = float(m.group(1)), float(m.group(2)), int(m.group(3))
        mat = '白色'
        if '双面红' in s: mat = '特硬'
        elif '双面黑' in s: mat = '特硬'
        return (mat, sorted([l, w, h], reverse=True), '外径')
    
    # 4. 【E坑高度Hcm】材料;3层;扣底盒【长X宽LxW】n个一组
    m = re.search(r'【E坑高度(\d+)cm】(.+?)[^；;]*[；;]\d+层[^；;]*[；;]扣底盒【长X宽(\d+)X(\d+)】', s)
    if m:
        h, l, w = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mat_raw = m.group(2)
        if '牛皮特硬原色' in mat_raw: mat = 'P6D'
        else: mat = '白色'
        return (mat, sorted([l, w, h], reverse=True), '扣底盒')
    
    # 5. X号信封专用【L*W*H】
    m = re.search(r'信封专用【(\d+)\*(\d+)\*(\d+)】', s)
    if m: return ('优质', sorted([int(m.group(1)), int(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # 6. A4纸专用【L*W*H】
    m = re.search(r'A4纸专用【([\d.]+)\*([\d.]+)\*([\d.]+)】', s)
    if m: return ('优质', sorted([round(float(m.group(1))), round(float(m.group(2))), round(float(m.group(3)))], reverse=True), '内径')
    
    # 7. 纸箱【高度Hcm】/n个一组;5层;纸箱外径-/长x宽【LxWcm】
    m = re.search(r'纸箱【高度(\d+)cm】/\d+个一组[^；;]*[；;]\d+层[^；;]*[；;]纸箱外径[^；;]*长x宽【([\d.]+)x([\d.]+)cm】', s)
    if m: return ('EB', sorted([float(m.group(2)), float(m.group(3)), int(m.group(1))], reverse=True), '外径')
    
    # 8. 宽【Wcm】高【Hcm】内径;【n个】长【Lcm】
    m = re.search(r'宽【(\d+)cm】高【(\d+)cm】内径[^；;]*[；;]【\d+个】长【(\d+)cm】', s)
    if m: return ('特硬', sorted([int(m.group(3)), int(m.group(1)), int(m.group(2))], reverse=True), '内径')
    
    return None

df_nm = pd.read_excel(nm_path)
mask = df_nm['店铺简称'].str.contains('止合', na=False)
zh = df_nm[mask].copy().reset_index(drop=True)
print(f'天猫止合在无匹配中: {len(zh)} 条')

matched_new = []
nomatch_new = []
stats = {}
SHOP_FULL = '飞机盒止合专卖店'

for idx, (_, row) in enumerate(zh.iterrows()):
    pid = str(row['平台商品id']).strip()
    spec_id = str(row['平台规格id']).strip()
    spec_name = str(row['规格名称']).strip()
    shop = str(row['店铺简称']).strip()
    
    result = parse_zh(spec_name)
    
    if result and result[1][0] is not None:
        mat, dims, dk = result
        ret_code = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), dk, mat)
        dims_out = f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-{dk}-{mat}'
        
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['匹配'] = stats.get('匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['无匹配'] = stats.get('无匹配', 0) + 1
    else:
        stats['未识别'] = stats.get('未识别', 0) + 1

print('\n=== 统计 ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')
print(f'匹配成功: {len(matched_new)}')
print(f'无匹配: {len(nomatch_new)}')

if matched_new:
    okdir = r'D:\Desktop\换绑输出\OK文件'
    from glob import glob
    pat = os.path.join(okdir, '换绑文件_第*.xlsx')
    existing = []
    for f in os.listdir(okdir):
        if f.startswith('换绑文件_第') and f.endswith('.xlsx') and '部分' not in f:
            m = re.search(r'第(\d+)批', f)
            if m: existing.append(int(m.group(1)))
    batch = max(existing) + 1 if existing else 40
    
    fname = os.path.join(okdir, f'换绑文件_第{batch}批.xlsx')
    pd.DataFrame(matched_new, columns=['店铺名称', '平台商品id', '平台规格id', '商品编码']).to_excel(fname, index=False)
    import openpyxl
    wb = openpyxl.load_workbook(fname)
    ws = wb.active
    ws.insert_rows(1)
    ws.cell(1, 2).value = '商品对应表'
    wb.save(fname)
    print(f'✅ 换绑文件_第{batch}批: {len(matched_new)}条')

# 从无匹配中删除止合
zh_processed = set(zh['平台规格id'].dropna().astype(str).str.strip())
mask_keep = ~df_nm['平台规格id'].astype(str).isin(zh_processed)
left = df_nm[mask_keep]
left.to_excel(nm_path, index=False)
print(f'✅ 无匹配已更新: 剩余{len(left)}条（移除了{len(zh_processed)}条止合）')
