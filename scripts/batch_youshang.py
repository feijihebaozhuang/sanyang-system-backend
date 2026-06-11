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
        key = (float(l), float(w), float(h))
        vals = tuple(sorted(key))
        fk = (vals[0], vals[1], vals[2], dk)
        candidates = fuzzy_idx.get(fk, [])
        for c, cm in candidates:
            if mat in cm or cm in mat or cm == mat:
                return c
        if candidates: return candidates[0][0]
    except: pass
    return None

def dfmt(v):
    s = f'{v:.1f}'; return s.rstrip('0').rstrip('.')

def mat_map(mat_raw):
    """材料映射"""
    m = mat_raw.strip().replace('；','').replace(';','').strip()
    if not m: return '无色'
    # 特硬 - 白系列 → 白色
    if '双面白色' in m or '双面白' in m: return '白色'
    if '特硬双面白' in m: return '白色'
    # 白色
    if m == '白色' or m == '白色纸': return '白色'
    # 台湾纸/超硬台湾 → 超硬
    if '台湾纸超硬' in m or '超硬台湾纸' in m or '超硬台湾' in m or '台湾黄超硬' in m or '台湾纸超硬黄' in m:
        return '超硬'
    if '台湾纸超硬' in m: return '超硬'
    if '台湾纸黄色' in m or '台湾黄' in m: return '超硬'
    if '台湾纸' in m: return '超硬'
    # 超硬
    if '超硬' in m: return '超硬'
    # 黄色 → 关联到特硬
    if '黄色' in m:
        if '特硬' in m: return '特硬'
        if '超硬' in m: return '超硬'
        return '特硬'
    # 特硬
    if '特硬' in m: return '特硬'
    # 特惠 → 特硬
    if '特惠' in m: return '特硬'
    # 牛皮色
    if '牛皮色' in m: return '特硬'
    # 优质牛卡 → 优质
    if '优质牛卡' in m or '优质' in m: return '优质'
    # 原色
    if '原色' in m: return '特硬'
    if '白色' in m: return '白色'
    return m

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
    
    ret_code = None; dims_out = None; dk = '外径'
    parsed = False
    
    # ========== ① 优质牛卡: 材料【数量】*LxWxH ==========
    m1 = re.search(r'优质牛卡【(\d+)个】\*([\d.]+)x([\d.]+)x([\d.]+)', spec_name)
    if m1:
        l, w, h = float(m1.group(2)), float(m1.group(3)), float(m1.group(4))
        l, w = max(l, w), min(l, w)
        ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', '优质')
        dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-优质'
        parsed = True
    
    # ========== ② 内径mm: 材料-数量【Hmm/厘米高】;L*W【长宽mm】【内径尺寸】 ==========
    if not parsed:
        m2 = re.search(r'(.+?)-(\d+)个【(\d+)(?:mm|厘米)高】;(\d+)\*(\d+)(?:\*)?【长宽】?MM?【内径尺寸】', spec_name)
        if m2:
            mat_raw = m2.group(1); h_val = int(m2.group(3)); x_mm = int(m2.group(4)); y_mm = int(m2.group(5))
            mat = mat_map(mat_raw)
            h = h_val  # cm就是cm, mm转cm已经在上面
            if 'mm' in re.search(r'【(\d+)(mm|厘米)高】', spec_name).group(2): h = round(h_val / 10, 1)
            x = round(x_mm / 10, 1); y = round(y_mm / 10, 1)
            l, w = max(x, y), min(x, y)
            ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '内径', mat)
            dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-内径-{mat}'
            parsed = True
    
    # ========== ②b 内径mm厘米高: 材料-数量【H厘米高】;L*W【长宽】MM【内径尺寸】 ==========
    if not parsed:
        m2b = re.search(r'(.+?)-(\d+)个【(\d+)厘米高】;(\d+)\*(\d+)(?:\*)?【长宽】MM【内径尺寸】', spec_name)
        if m2b:
            mat_raw = m2b.group(1); h_cm = int(m2b.group(3)); x_mm = int(m2b.group(4)); y_mm = int(m2b.group(5))
            mat = mat_map(mat_raw)
            h = h_cm; x = round(x_mm / 10, 1); y = round(y_mm / 10, 1)
            l, w = max(x, y), min(x, y)
            ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '内径', mat)
            dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-内径-{mat}'
            parsed = True
    
    # ========== ③ 内径直接: 材料【内径】【数量】*或x L*W*H ==========
    if not parsed:
        m3 = re.search(r'(.+?)【内径】【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', spec_name)
        if m3:
            mat_raw = m3.group(1); lv = int(m3.group(3)); wv = int(m3.group(4)); hv = int(m3.group(5))
            mat = mat_map(mat_raw)
            dims = sorted([lv, wv, hv], reverse=True)
            ret_code = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), '内径', mat)
            dims_out = f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-内径-{mat}'
            parsed = True
    
    # ========== ④ 外尺寸/外径: 材料【外径】【数量】*或x L*W*H 或 材料-外尺寸【数量】*L*W*H ==========
    if not parsed:
        m4 = re.search(r'(.+?)(?:-外尺寸|【外径】)【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', spec_name)
        if m4:
            mat_raw = m4.group(1); lv = int(m4.group(3)); wv = int(m4.group(4)); hv = int(m4.group(5))
            mat = mat_map(mat_raw)
            dims = sorted([lv, wv, hv], reverse=True)
            ret_code = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), '外径', mat)
            dims_out = f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-外径-{mat}'
            parsed = True
    
    # ========== ④b 外尺寸【长宽】LxWcm；层【纸箱】【高】Hcm ==========
    if not parsed:
        m4b = re.search(r'外尺寸 【长宽】([\d.]+)x([\d.]+)cm[^；;]*[；;].*?【高】([\d.]+)cm', spec_name)
        if m4b:
            l, w, h = float(m4b.group(1)), float(m4b.group(2)), float(m4b.group(3))
            l, w = max(l, w), min(l, w)
            ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', '特硬')
            dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-特硬'
            parsed = True
    
    # ========== ⑤ 纸箱类汇总 ==========
    # 高Hcm【层】；长宽【L*W】
    if not parsed:
        m5 = re.search(r'高(\d+)cm【(\d+)层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】', spec_name)
        if not m5:
            # LxW cm【长宽】;高度Hcm【层纸箱】数量
            m5 = re.search(r'([\d.]+)x([\d.]+)\s*cm【长宽】[^；;]*[；;]高度(\d+)cm【(.+?)(?:纸箱|纸箱】)', spec_name)
        if not m5:
            # LxW cm【长宽】;Hcm 高【层纸箱】数量
            m5 = re.search(r'([\d.]+)x([\d.]+)\s*cm【长宽】[^；;]*[；;](\d+)cm\s*高【(.+?)(?:纸箱|纸箱】)', spec_name)
        if m5:
            lv, wv = float(m5.group(1)), float(m5.group(2))
            h = int(m5.group(3))
            mat_raw = m5.group(4) if len(m5.groups()) >= 4 else '特硬'
            mat = mat_map(mat_raw)
            l, w = max(lv, wv), min(lv, wv)
            ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', mat)
            dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-{mat}'
            parsed = True
    
    # ========== ⑤b 长宽 L*W；【五层材料】数量；高Hcm（纸箱类） ==========
    if not parsed:
        m5b = re.search(r'长宽\s*([\d.]+)\s*\*\s*([\d.]+)[^；;]*[；;]【(.+?)】\s*\d+个装[^；;]*[；;]高(\d+)cm', spec_name)
        if m5b:
            lv, wv = float(m5b.group(1)), float(m5b.group(2))
            mat_raw = m5b.group(3)
            h = int(m5b.group(4))
            mat = mat_map(mat_raw)
            l, w = max(lv, wv), min(lv, wv)
            ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', mat)
            dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-{mat}'
            parsed = True
    
    # ========== ⑥ 直接格式: 材料-数量*LxWxH ==========
    if not parsed:
        m6 = re.search(r'(.+?)-(\d+)个[\*x]([\d.]+)[\*x]([\d.]+)[\*x]([\d.]+)', spec_name)
        if m6:
            mat_raw = m6.group(1)
            lv, wv, hv = float(m6.group(3)), float(m6.group(4)), float(m6.group(5))
            mat = mat_map(mat_raw)
            dims = sorted([lv, wv, hv], reverse=True)
            ret_code = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), '外径', mat)
            dims_out = f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-外径-{mat}'
            parsed = True
    
    # ========== ⑦ 长【L】cm；宽【W】cm；层材料 ==========
    if not parsed:
        m7 = re.search(r'长【(\d+)】cm[^；;]*[；;]宽【(\d+)】cm[^；;]*[；;](\d+)层(.+?)【', spec_name)
        if m7:
            lv, wv, layer, mat_raw = int(m7.group(1)), int(m7.group(2)), int(m7.group(3)), m7.group(4)
            mat = mat_map(mat_raw)
            l, w = max(lv, wv), min(lv, wv)
            h = 999  # 无高度信息，按纸箱默认
            ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', mat)
            dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-{mat}'
            parsed = True
    
    # ========== ⑧ 外尺寸【长宽】LxWcm；层纸箱/飞机盒 无高度 ==========
    if not parsed:
        m8 = re.search(r'外尺寸 【长宽】([\d.]+)x([\d.]+)cm[^；;]*[；;]【纸箱】&【飞机盒】', spec_name)
        if m8:
            lv, wv = float(m8.group(1)), float(m8.group(2))
            l, w = max(lv, wv), min(lv, wv)
            h = 999
            ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', '特硬')
            dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-特硬'
            parsed = True
    
    # ========== ⑨ 长Lmm；【宽高】W*Hmm；材料 ==========
    if not parsed:
        m9 = re.search(r'长(\d+)mm[^；;]*[；;]【宽高】(\d+)\*(\d+)mm[^；;]*[；;](.+?)(?:;|$)', spec_name)
        if m9:
            l_mm = int(m9.group(1)); w_mm = int(m9.group(2)); h_mm = int(m9.group(3)); mat_raw = m9.group(4)
            mat = mat_map(mat_raw)
            # mm→cm
            l = round(l_mm / 10, 1); w = round(w_mm / 10, 1); h = round(h_mm / 10, 1)
            dims = sorted([l, w, h], reverse=True)
            # 优质特价外尺寸 → 外径
            dk = '外径' if '外尺寸' in mat_raw else '内径'
            ret_code = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), dk, mat)
            dims_out = f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-{dk}-{mat}'
            parsed = True
    
    # ========== ⑩ 24cm高度以上 加工定制：长宽【L*Wcm】 ==========
    if not parsed:
        m10 = re.search(r'长宽【([\d.]+)\*([\d.]+)cm】', spec_name)
        if m10 and '高度' in spec_name:
            lv, wv = float(m10.group(1)), float(m10.group(2))
            l, w = max(lv, wv), min(lv, wv)
            h = 24  # 24cm高度以上
            ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', '特硬')
            dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-特硬'
            parsed = True
    
    if parsed:
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['匹配'] = stats.get('匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['无匹配'] = stats.get('无匹配', 0) + 1
    else:
        stats['未识别'] = stats.get('未识别', 0) + 1
    
    if (idx + 1) % 5000 == 0:
        print(f'  已处理 {idx+1}/{len(target)}...({stats.get("匹配",0)}匹配, {stats.get("无匹配",0)}无匹配, {stats.get("未识别",0)}未识别)')

print('\n=== 统计 ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')
print(f'\n匹配成功: {len(matched_new)}')
print(f'无匹配: {len(nomatch_new)}')
print(f'未识别: {stats.get("未识别", 0)}')

# ===== 换绑文件 =====
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

# ===== 无匹配 =====
if nomatch_new:
    rows_to_add = [r for r in nomatch_new if r[3] not in nomatched_existing]
    if rows_to_add:
        if os.path.exists(nm_path):
            df_nm = pd.read_excel(nm_path)
            pd.concat([df_nm, pd.DataFrame(rows_to_add, columns=['店铺简称', '平台商品id', '规格名称', '平台规格id', '标记', '尝试解析'])], ignore_index=True).to_excel(nm_path, index=False)
        else:
            pd.DataFrame(rows_to_add, columns=['店铺简称', '平台商品id', '规格名称', '平台规格id', '标记', '尝试解析']).to_excel(nm_path, index=False)
        print(f'✅ 追加{len(rows_to_add)}条到无匹配')

# ===== 更新平卡 =====
processed_ids = {r[2] for r in matched_new} | {r[3] for r in nomatch_new}
mask_keep = ~df['平台规格id'].astype(str).isin(processed_ids)
df_keep = df[mask_keep]
df_keep.to_excel(PINGKA, index=False)
print(f'✅ 平卡已更新: {len(df_keep)}条')
