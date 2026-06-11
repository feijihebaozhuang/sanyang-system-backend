# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'
PINGKA = os.path.join(OUT_DIR, '平卡_待处理.xlsx')

km = pd.read_excel(r'd:\Desktop\快麦商品 - 副本.xlsx', sheet_name='报表1', header=3, dtype=str, usecols=[0])
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
print(f'快麦商品: {len(all_codes)} 条')

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

def mat_map(m):
    if not m: return '无色'
    m = m.strip().replace('；','').replace(';','')
    if '双面白色' in m or '双面白' in m or '特硬双面白' in m: return '白色'
    if '白盒' in m: return '白色'
    if m == '白色' or m == '白色纸': return '白色'
    if '超硬台湾' in m or '台湾纸超硬' in m or '台湾黄超硬' in m: return '超硬'
    if '台湾纸' in m or '台湾黄' in m: return '超硬'
    if '超硬' in m: return '超硬'
    if '超级' in m: return '超硬'
    if '特惠' in m: return '特硬'
    if '特硬' in m or '特价' in m: return '特硬'
    if '黄色' in m: return '特硬'
    if '牛皮色' in m or '牛皮' in m: return '特硬'
    if '原色' in m: return '特硬'
    if '玖龙' in m or 'S级' in m: return '特硬'
    if 'E坑' in m: return '特硬'
    if '加强' in m: return '特硬'
    if '高档' in m: return '特硬'
    if '优质' in m: return '优质'
    if '白色' in m or '白' in m: return '白色'
    if '红色' in m: return '特硬'
    return m.strip()

def parse_spec(s):
    s = s.strip()
    
    # ===== [Hcm高]材料-数量;L*W单位(无长宽标记) =====
    # 高度24cm【五层纸箱】50个;长宽47x37mm
    m = re.search(r'高度(\d+)cm【.+?纸箱】\s*(\d+)个[^；;]*[；;]长宽([\d.]+)x([\d.]+)\s*(mm|cm)', s)
    if m:
        h = int(m.group(1))
        lw_u = m.group(5)
        if lw_u == 'mm':
            l = round(float(m.group(3))/10, 1)
            w = round(float(m.group(4))/10, 1)
        else:
            l, w = float(m.group(3)), float(m.group(4))
        return ('特硬', sorted([l, w, h], reverse=True), '内径')
    
    # 高度24cm【五层纸箱】50个;L*W【长宽】MM/无标记
    m = re.search(r'高度(\d+)cm【.+?纸箱】\s*(\d+)个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?(?:【.*?)?(?:;|$)', s)
    if m:
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '内径')
    
    # 高度24cm【五层纸箱】50个;L*Wmm(无长宽无单位标记)
    m = re.search(r'高度(\d+)cm【.+?纸箱】\s*(\d+)个[^；;]*[；;](\d+)\*(\d+)(?:\*?)(?:mm|MM)?(?:;|$)', s)
    if m:
        l_mm, w_mm = int(m.group(3)), int(m.group(4))
        return ('特硬', sorted([round(l_mm/10,1), round(w_mm/10,1), int(m.group(1))], reverse=True), '内径')
    
    # ===== 高Hcm【五层】；长宽【L*W】数量 =====
    # 高12cm【五层】；长宽【29*21】100个
    m = re.search(r'高(\d+)cm【\d+层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】', s)
    if m:
        return ('特硬', sorted([float(m.group(2)), float(m.group(3)), int(m.group(1))], reverse=True), '外径')
    
    # ===== 【H厘米高】材料-数量;L*W【长宽】MM（无cm单位） =====
    # 【2厘米高】双面白-100个;100*70mm【长宽】
    m = re.search(r'【(\d+)厘米高】(.+?)-(\d+)个[^；;]*[；;](\d+)\*(\d+)mm【长宽】', s)
    if m:
        l_mm, w_mm = int(m.group(4)), int(m.group(5))
        return (mat_map(m.group(2)), sorted([round(l_mm/10,1), round(w_mm/10,1), int(m.group(1))], reverse=True), '内径')
    
    # 【2厘米高】材料-数量;L*W*【长宽】MM/【内径】
    m = re.search(r'【(\d+)厘米高】(.+?)-(\d+)个[^；;]*[；;](\d+)\*(\d+)\*?【长宽】\s*(?:CM|cm|MM|mm)?(?:【内径.*?)?(?:;|$)', s)
    if m:
        return (mat_map(m.group(2)), sorted([float(m.group(4)), float(m.group(5)), int(m.group(1))], reverse=True), '内径')
    
    # ===== 材料-数量【H厘米高】;L*W*【长宽】mm/CM =====
    # 台湾纸-100个【10厘米高】;410*180*【长宽】mm
    m = re.search(r'(.+?)-(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)\*【长宽】\s*(?:mm|MM|cm|CM)?', s)
    if m:
        return (mat_map(m.group(1)), sorted([int(m.group(4)), int(m.group(5)), int(m.group(3))], reverse=True), '内径')
    
    # ===== 材料-数量【H厘米高】;无长宽标记 =====
    # 特硬-100个【2厘米高】;28*8【长宽】 【内径】
    m = re.search(r'(.+?)-(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】\s*(?:CM|cm)?(?:【.*?)?(?:;|$)', s)
    if m:
        return (mat_map(m.group(1)), sorted([int(m.group(4)), int(m.group(5)), int(m.group(3))], reverse=True), '内径')
    
    # ===== 材料-数量【Hmm高】;L*W【长宽mm】 =====
    m = re.search(r'(.+?)-(\d+)个【(\d+)mm高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽mm】?(?:【.*?)?(?:;|$)', s)
    if m:
        l_mm, w_mm, h_mm = int(m.group(4)), int(m.group(5)), int(m.group(3))
        return (mat_map(m.group(1)), sorted([round(l_mm/10,1), round(w_mm/10,1), round(h_mm/10,1)], reverse=True), '内径')
    
    # ===== 材料50个【H厘米高】;L*W【长宽】mm =====
    m = re.search(r'(.+?)(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(4)), float(m.group(5)), int(m.group(3))], reverse=True), '内径')
    
    # ===== 材料 数量个【H厘米高】【内径尺寸】;L*Wmm =====
    # 白色 50个【9厘米高】【内径尺寸】;510*240【长宽】mm
    m = re.search(r'(.+?)\s+(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(4)), float(m.group(5)), int(m.group(3))], reverse=True), '内径')
    
    # ===== 材料【数量】*LxWxH（已经处理过，但确保兜底） =====
    m = re.search(r'^(.+?)(?:\d+个)?【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True), '外径')
    
    # ===== 数量前导*LxWxH =====
    # 100个材料*LxWxH
    m = re.search(r'^(\d+)个(.+?)[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        return (mat_map(m.group(2)), sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True), '外径')
    
    # ===== 颜色【数量/组】*LxWxH =====
    m = re.search(r'^(.+?)【(.+?)】[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True), '外径')
    
    # ===== 颜色数量个/组*LxWxH =====
    m = re.search(r'^(.+?)(?:\d+个[组/]*)[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(2)), float(m.group(3)), float(m.group(4))], reverse=True), '外径')
    
    # ===== 高度Hcm【层纸箱】数量;L*W【长宽mm】xxx =====
    m = re.search(r'高度(\d+)cm【.+?纸箱】\s*(\d+)个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?', s)
    if m:
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '内径')
    
    return None


df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
print(f'阿里友尚剩余: {len(target)} 条')

nomatched_existing = set()
nm_path = os.path.join(OUT_DIR, '无匹配_待处理.xlsx')
if os.path.exists(nm_path):
    df_nm = pd.read_excel(nm_path)
    nomatched_existing = set(df_nm['平台规格id'].dropna().astype(str).str.strip())

matched_new = []
nomatch_new = []
stats = {}
SHOP_FULL = '友尚包装'

for idx, (_, row) in enumerate(target.iterrows()):
    pid = str(row['平台商品id']).strip()
    spec_id = str(row['平台规格id']).strip()
    spec_name = str(row['规格名称']).strip()
    shop = str(row['店铺简称']).strip()
    
    if spec_id in nomatched_existing: continue
    
    result = parse_spec(spec_name)
    
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
    
    if (idx + 1) % 5000 == 0:
        print(f'  {idx+1}/{len(target)}...')

print('\n=== 统计 ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')
print(f'\n匹配成功: {len(matched_new)}')
print(f'无匹配: {len(nomatch_new)}')

if matched_new:
    batch = 1
    flist = [f for f in os.listdir(OUT_DIR) if f.startswith('换绑文件_第') and f.endswith('.xlsx') and '部分' not in f]
    if flist:
        nums = [int(re.search(r'第(\d+)批', f).group(1)) for f in flist if re.search(r'第(\d+)批', f)]
        batch = max(nums) + 1 if nums else 1
    fname = os.path.join(OUT_DIR, f'换绑文件_第{batch}批.xlsx')
    pd.DataFrame(matched_new, columns=['店铺名称', '平台商品id', '平台规格id', '商品编码']).to_excel(fname, index=False)
    print(f'✅ 换绑文件_第{batch}批: {len(matched_new)}条')
    if len(matched_new) > 3000:
        import math
        parts = math.ceil(len(matched_new) / 3000)
        for pi in range(parts):
            start = pi * 3000
            end = min((pi + 1) * 3000, len(matched_new))
            pfname = os.path.join(OUT_DIR, f'换绑文件_第{batch}批_第{pi+1}部分.xlsx')
            pd.DataFrame(matched_new[start:end], columns=['店铺名称', '平台商品id', '平台规格id', '商品编码']).to_excel(pfname, index=False)
        print(f'  已拆分为 {parts} 部分')

if nomatch_new:
    rows_to_add = [r for r in nomatch_new if r[3] not in nomatched_existing]
    if rows_to_add:
        if os.path.exists(nm_path):
            df_nm = pd.read_excel(nm_path)
            pd.concat([df_nm, pd.DataFrame(rows_to_add, columns=['店铺简称', '平台商品id', '规格名称', '平台规格id', '标记', '尝试解析'])], ignore_index=True).to_excel(nm_path, index=False)
        else:
            pd.DataFrame(rows_to_add, columns=['店铺简称', '平台商品id', '规格名称', '平台规格id', '标记', '尝试解析']).to_excel(nm_path, index=False)
        print(f'✅ 追加{len(rows_to_add)}条到无匹配')

processed_ids = {r[2] for r in matched_new} | {r[3] for r in nomatch_new}
mask_keep = ~df['平台规格id'].astype(str).isin(processed_ids)
df_keep = df[mask_keep]
df_keep.to_excel(PINGKA, index=False)
print(f'✅ 平卡已更新: {len(df_keep)}条')
