# -*- coding: utf-8 -*-
"""友尚最终轮"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'
files = os.listdir(OUT_DIR)
pingka_file = [f for f in files if f.startswith('\u5e73') and f.endswith('.xlsx')][0]
PINGKA = os.path.join(OUT_DIR, pingka_file)

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

def dfmt(v):
    s = f'{v:.1f}'.rstrip('0').rstrip('.')
    return s

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
    
    # === Z1: 超级超级硬n个【Hcm高];L*Wmm【内径尺寸】(无空格) ===
    # 超级超级硬50个【6厘米高];300*290mm【内径尺寸】
    m = re.search(r'超级超级硬(\d+)个【(\d+)厘米高[\]】][^；;]*[；;](\d+)\*(\d+)mm(?:【.*?)?(?:;|$)', s)
    if m:
        return ('超硬', sorted([round(int(m.group(3))/10,1), round(int(m.group(4))/10,1), int(m.group(2))], reverse=True), '内径')
    
    # === Z2: 超级超级硬n个【Hcm高];L*Wmm (无标记, 有重复段) ===
    # 超级超级硬50个【6厘米高];300*290mm;超级超级硬50个【6厘米高]
    m = re.search(r'超级超级硬(\d+)个【(\d+)厘米高[\]】][^；;]*[；;](\d+)\*(\d+)mm', s)
    if m:
        return ('超硬', sorted([round(int(m.group(3))/10,1), round(int(m.group(4))/10,1), int(m.group(2))], reverse=True), '内径')
    
    # === Z3: 长度Hcm---材料-n个组];L*W【长宽】MM ===
    # 长度11cm---特硬黄-50个组;350*110【长宽】MM
    m = re.search(r'长度(\d+)cm---(.+?)-(\d+)个[组\]]*[^；;]*[；;](\d+)\*(\d+)【长宽】', s)
    if m:
        l_mm = int(m.group(4))
        w_mm = int(m.group(5))
        h_cm = int(m.group(1))
        return (mat_map(m.group(2)), sorted([round(l_mm/10,1), round(w_mm/10,1), h_cm], reverse=True), '内径')
    
    # === Z4: 10号（L*W*H）；三层K 特硬；无扣手 ===
    # 10号（175*95*115）；三层K 特硬；无扣手
    m = re.search(r'\d+号[^（]*（(\d+)\*(\d+)\*(\d+)）[^；;]*[；;]三层K\s+特硬', s)
    if m:
        return ('特硬', sorted([int(m.group(1)), int(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # 10号半高（L*W*H）...
    m = re.search(r'\d+号[^（]*（(\d+)\*(\d+)\*(\d+)）[^；;]*[；;]三层K\s+特硬', s)
    if m:
        return ('特硬', sorted([int(m.group(1)), int(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # === Z5: 特价一组;【C3】：0.5*16.5*11cm （多了一个】） ===
    m = re.search(r'特价\s+\d+个一组[^；;]*[；;]【[^】]+】[：:]?\]([\d.]+)\*([\d.]+)\*([\d.]+)cm', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True), '外径')
    
    # 通用的特价格式
    m = re.search(r'特价\s+\d+个一组[^；;]*[；;]【[^】]+】[：:]*([\d.]+)\*([\d.]+)\*([\d.]+)cm', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True), '外径')
    
    # === Z6: 25*19.5*25外径五层纸箱；五层纸箱；黄色 ===
    m = re.search(r'([\d.]+)\*([\d.]+)\*([\d.]+)外径', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True), '外径')
    
    return None

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
print(f'阿里友尚剩余: {len(target)} 条')

nomatched_existing = set()
nm_path = os.path.join(OUT_DIR, '\u65e0\u5339\u914d_5f85\u5904\u7406.xlsx')
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

print('\n=== 统计 ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')

if matched_new:
    batch = 1
    flist = [f for f in os.listdir(OUT_DIR) if f.startswith('\u6362\u7ed1') and f.endswith('.xlsx') and '\u90e8\u5206' not in f]
    if flist:
        nums = [int(re.search(r'\u7b2c(\d+)\u6279', f).group(1)) for f in flist if re.search(r'\u7b2c(\d+)\u6279', f)]
        batch = max(nums) + 1 if nums else 1
    fname = os.path.join(OUT_DIR, f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{batch}\u6279.xlsx')
    pd.DataFrame(matched_new, columns=['店铺名称', '平台商品id', '平台规格id', '商品编码']).to_excel(fname, index=False)
    print(f'✅ 换绑文件_第{batch}批: {len(matched_new)}条')

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
