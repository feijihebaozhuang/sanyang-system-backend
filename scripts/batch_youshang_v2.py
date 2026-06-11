# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'
PINGKA = os.path.join(OUT_DIR, '平卡_待处理.xlsx')

# 快麦
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

def dfmt(v):
    s = f'{v:.1f}'
    return s.rstrip('0').rstrip('.')

def mat_map(m):
    if not m: return '无色'
    m = m.strip().replace('；','').replace(';','')
    if '双面白色' in m or '双面白' in m or '特硬双面白' in m: return '白色'
    if m == '白色' or m == '白色纸': return '白色'
    if '超硬台湾' in m or '台湾纸超硬' in m or '台湾黄超硬' in m or '超硬台湾' in m: return '超硬'
    if '台湾纸' in m: return '超硬'
    if '超硬' in m: return '超硬'
    if '特惠' in m: return '特硬'
    if '特硬' in m: return '特硬'
    if '黄色' in m: return '特硬'
    if '牛皮色' in m: return '特硬'
    if '原色' in m: return '特硬'
    if '优质' in m: return '优质'
    if '白色' in m: return '白色'
    return m.strip()

def parse_spec(s, pid, spec_id, shop):
    """解析一个规格名称，返回 (matched_code, dims_str) 或 (None, dims_str) 或 (None, None)"""
    
    # ---- 格式A: 材料-数量【Hmm/厘米高】;L*W【长宽】【内径尺寸】 ----
    #  例: 特硬-50个【100mm高】;230*220【长宽mm】【内径尺寸】
    #  例: 特硬黄-100个【10厘米高】;270*170【长宽】MM【内径尺寸】
    m = re.search(r'^(.+?)-(\d+)个【(\d+)(?:mm|厘米)高】[^；;]*[；;](\d+)\*(\d+)(?:\*)?【长宽】?MM?【内径尺寸】', s)
    if m:
        mat = mat_map(m.group(1))
        h_val = int(m.group(3))
        h = round(h_val / 10, 1) if 'mm' in s[s.index('【'):s.index('】')] else h_val
        x = round(int(m.group(4)) / 10, 1); y = round(int(m.group(5)) / 10, 1)
        l, w = max(x, y), min(x, y)
        c = match_3d(dfmt(l), dfmt(w), dfmt(h), '内径', mat)
        return c, f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-内径-{mat}'
    
    # ---- 格式B: 材料【内径】【数量】*L*W*H 或 x分隔 ----
    #  例: 特惠【内径】【100个】*220*220*100
    #  例: 特惠【内径】【100个】*140x140x100
    m = re.search(r'^(.+?)【内径】【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        mat = mat_map(m.group(1))
        dims = sorted([int(m.group(3)), int(m.group(4)), int(m.group(5))], reverse=True)
        c = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), '内径', mat)
        return c, f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-内径-{mat}'
    
    # ---- 格式C: 材料【外径】【数量】*L*W*H 或 材料-外尺寸【数量】*L*W*H ----
    #  例: 特惠【外径】【100个】*220*220*100
    #  例: 台湾纸-外尺寸【100个】*220*220*100
    m = re.search(r'^(.+?)(?:-外尺寸|【外径】)【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        mat = mat_map(m.group(1))
        dims = sorted([int(m.group(3)), int(m.group(4)), int(m.group(5))], reverse=True)
        c = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), '外径', mat)
        return c, f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-外径-{mat}'
    
    # ---- 格式D: 优质牛卡【数量】*LxWxH ----
    m = re.search(r'优质牛卡【(\d+)个】\*([\d.]+)x([\d.]+)x([\d.]+)', s)
    if m:
        l, w, h = float(m.group(2)), float(m.group(3)), float(m.group(4))
        l, w = max(l, w), min(l, w)
        c = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', '优质')
        return c, f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-优质'
    
    # ---- 格式E: 材料-数量*LxWxH（直接格式）----
    #  例: 白色-100个*16*10*2.3
    #  例: 黄色-100个*16x10.5x4
    m = re.search(r'^(.+?)-(\d+)个[\*x]([\d.]+)[\*x]([\d.]+)[\*x]([\d.]+)', s)
    if m:
        mat = mat_map(m.group(1))
        lv, wv, hv = float(m.group(3)), float(m.group(4)), float(m.group(5))
        dims = sorted([lv, wv, hv], reverse=True)
        c = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), '外径', mat)
        return c, f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-外径-{mat}'
    
    # ---- 格式F: 外尺寸【长宽】LxWcm；3层【纸箱】【高】Hcm ----
    m = re.search(r'外尺寸 【长宽】([\d.]+)x([\d.]+)cm[^；;]*[；;].*?【高】(\d+)cm', s)
    if m:
        l, w, h = float(m.group(1)), float(m.group(2)), int(m.group(3))
        l, w = max(l, w), min(l, w)
        c = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', '特硬')
        return c, f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-特硬'
    
    # ---- 格式G: 外尺寸【长宽】LxWcm；【纸箱】&【飞机盒】----
    m = re.search(r'外尺寸 【长宽】([\d.]+)x([\d.]+)cm[^；;]*[；;]【纸箱】&【飞机盒】', s)
    if m:
        l, w = float(m.group(1)), float(m.group(2))
        l, w = max(l, w), min(l, w)
        c = match_3d(dfmt(l), dfmt(w), '24', '外径', '特硬')
        return c, f'{dfmt(l)}*{dfmt(w)}*24-外径-特硬'
    
    # ---- 格式H: 高Hcm【层】；长宽【L*W】----
    #  例: 高12cm【5层】；长宽【15*12】
    m = re.search(r'高(\d+)cm【(\d+)层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】', s)
    if m:
        h = int(m.group(1)); lv, wv = float(m.group(3)), float(m.group(4))
        l, w = max(lv, wv), min(lv, wv)
        c = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', '特硬')
        return c, f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-特硬'
    
    # ---- 格式I: LxW cm【长宽】;高度Hcm【层纸箱】数量 ----
    #  例: 34x33 cm【长宽】;37cm 高【五层纸箱】50个
    #  例: 16x15 cm【长宽】;高度37cm【五层纸箱】50个
    m = re.search(r'([\d.]+)x([\d.]+)\s*cm【长宽】[^；;]*[；;](?:高度|)(\d+)cm\s*高【(.+?)(?:纸箱|纸箱】)', s)
    if m:
        lv, wv, h = float(m.group(1)), float(m.group(2)), int(m.group(3))
        mat = mat_map(m.group(4))
        l, w = max(lv, wv), min(lv, wv)
        c = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', mat)
        return c, f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-{mat}'
    
    # ---- 格式J: 长宽 L*W；【五层材料】数量；高Hcm ----
    #  例: 长宽 20*20；【五层特硬】10个装；高25cm
    m = re.search(r'长宽\s*([\d.]+)\s*\*\s*([\d.]+)[^；;]*[；;]【(.+?)】\s*\d+个装[^；;]*[；;]高(\d+)cm', s)
    if m:
        lv, wv = float(m.group(1)), float(m.group(2))
        mat = mat_map(m.group(3))
        h = int(m.group(4))
        l, w = max(lv, wv), min(lv, wv)
        c = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', mat)
        return c, f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-{mat}'
    
    # ---- 格式K: 高度Hcm【层纸箱】数量;L*W【长宽mm】----
    #  例: 高度24cm【五层纸箱】50个;310*300【长宽mm】
    m = re.search(r'高度(\d+)cm【(.+?)(?:纸箱|纸箱】)\s*\d+个[^；;]*[；;](\d+)\*(\d+)【长宽mm】', s)
    if m:
        h = int(m.group(1)); mat = mat_map(m.group(2)); x = int(m.group(3)); y = int(m.group(4))
        x = round(x / 10, 1); y = round(y / 10, 1)
        l, w = max(x, y), min(x, y)
        c = match_3d(dfmt(l), dfmt(w), dfmt(h), '内径', mat)
        return c, f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-内径-{mat}'
    
    # ---- 格式L: 24cm高度以上 加工定制；长宽【L*Wcm】----
    m = re.search(r'24cm高度以上.*?长宽【([\d.]+)\*([\d.]+)cm】', s)
    if m:
        l, w = float(m.group(1)), float(m.group(2))
        l, w = max(l, w), min(l, w)
        c = match_3d(dfmt(l), dfmt(w), '24', '外径', '特硬')
        return c, f'{dfmt(l)}*{dfmt(w)}*24-外径-特硬'
    
    # ---- 格式M: 长【L】cm；宽【W】cm；层材料 ----
    m = re.search(r'长【(\d+)】cm[^；;]*[；;]宽【(\d+)】cm[^；;]*[；;](\d+)层(.+?)【', s)
    if m:
        lv, wv, mat_raw = int(m.group(1)), int(m.group(2)), m.group(4)
        mat = mat_map(mat_raw)
        l, w = max(lv, wv), min(lv, wv)
        # 高度取999（纸卷类无高度）
        c = match_3d(dfmt(l), dfmt(w), '999', '外径', mat)
        return c, f'{dfmt(l)}*{dfmt(w)}*999-外径-{mat}'
    
    # ---- 格式N: 长Lmm；【宽高】W*Hmm；材料 ----
    m = re.search(r'长(\d+)mm[^；;]*[；;]【宽高】(\d+)\*(\d+)mm[^；;]*[；;](.+?)(?:;|$)', s)
    if m:
        l_mm, w_mm, h_mm = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mat_raw = m.group(4)
        mat = mat_map(mat_raw)
        l, w, h = round(l_mm/10,1), round(w_mm/10,1), round(h_mm/10,1)
        dims = sorted([l, w, h], reverse=True)
        dk = '外径' if '外尺寸' in mat_raw else '内径'
        c = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), dk, mat)
        return c, f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-{dk}-{mat}'
    
    return None, None


df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains('友尚', na=False)
target = df[mask].copy()
print(f'阿里友尚共 {len(target)} 条')

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
    
    ret_code, dims_out = parse_spec(spec_name, pid, spec_id, shop)
    
    if dims_out is not None:
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['匹配'] = stats.get('匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['无匹配'] = stats.get('无匹配', 0) + 1
    else:
        stats['未识别'] = stats.get('未识别', 0) + 1
    
    if (idx + 1) % 5000 == 0:
        pct = (idx+1)/len(target)*100
        print(f'  {idx+1}/{len(target)} ({pct:.0f}%)...匹配{stats.get("匹配",0)} 无匹配{stats.get("无匹配",0)} 未识别{stats.get("未识别",0)}')

print('\n=== 统计 ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')
print(f'\n匹配成功: {len(matched_new)}')
print(f'无匹配: {len(nomatch_new)}')
print(f'未识别: {stats.get("未识别", 0)}')

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
