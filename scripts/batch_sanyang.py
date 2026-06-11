# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'd:\Desktop\换绑输出'
PINGKA = os.path.join(OUT_DIR, '平卡_待处理.xlsx')
SHOP_KEY = '三羊'
SHOP_FULL = '三羊包装'

# 快麦数据
KUAMAI = r'd:\Desktop\快麦商品 - 副本.xlsx'
km = pd.read_excel(KUAMAI, sheet_name='报表1', header=3, dtype=str, usecols=[0])
all_codes = set()
for row in km.values:
    code = str(row[0] or '').strip()
    if code:
        all_codes.add(code)
print(f'快麦商品: {len(all_codes)} 条')

# 建立模糊索引
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
                fuzzy_idx.setdefault(fk, []).append(code)
            except:
                pass

def match_3d(l, w, h, dk, mat):
    """按 L*W*H-内外径-材料 匹配快麦"""
    code = f'{l}*{w}*{h}-{dk}-{mat}'
    if code in all_codes:
        return code
    code2 = f'{w}*{l}*{h}-{dk}-{mat}'
    if code2 in all_codes:
        return code2
    # 模糊匹配: 按排序后的三维+内外径
    try:
        key = (float(l), float(w), float(h))
        vals = tuple(sorted(key))
        fk = (vals[0], vals[1], vals[2], dk)
        candidates = fuzzy_idx.get(fk, [])
        for c in candidates:
            if mat in c or c.endswith(mat):
                return c
        if candidates:
            return candidates[0]  # 只要有尺寸内外径匹配就取第一个
    except:
        pass
    return None

def dfmt(v):
    s = f'{v:.1f}'
    return s.rstrip('0').rstrip('.')

def mat_map(mat_raw):
    m = mat_raw.strip().replace('；', '').replace(';', '').strip()
    if not m:
        return '无色'
    if '特硬双面白' in m or '特硬双面白色' in m or '5级特硬双面白' in m:
        return '白色'
    if '特硬原色' in m or '特硬' in m:
        return '特硬'
    if '超硬' in m:
        return '特硬'
    if '白色' in m:
        return '白色'
    if '牛皮色' in m:
        return '特硬'
    if '无色' in m:
        return '无色'
    return m

df = pd.read_excel(PINGKA)
mask = df['店铺简称'].str.contains(SHOP_KEY, na=False)
target = df[mask].copy()
print(f'阿里三羊共 {len(target)} 条')

nomatched_existing = set()
nm_path = os.path.join(OUT_DIR, '无匹配_待处理.xlsx')
if os.path.exists(nm_path):
    df_nm = pd.read_excel(nm_path)
    nomatched_existing = set(df_nm['平台规格id'].dropna().astype(str).str.strip())

matched_new = []
nomatch_new = []
stats = {}

for idx, (_, row) in enumerate(target.iterrows()):
    pid = str(row['平台商品id']).strip()
    spec_id = str(row['平台规格id']).strip()
    spec_name = str(row['规格名称']).strip()
    shop = str(row['店铺简称']).strip()
    
    if spec_id in nomatched_existing:
        continue
    
    parsed = False
    ret_code = None
    dims_out = None
    
    # ① 长*宽【L*W】cm;外尺寸材料【H cm高】（注意数字中间可能有空格如 12 .5 或 2 .5）
    m1 = re.search(r'长\*宽【([\d.\s]+)\*([\d.\s]+)】\s*cm;外尺寸([^【]*?)【([\d.\s]+)cm高】', spec_name)
    if m1:
        l_raw = m1.group(1).replace(' ', ''); w_raw = m1.group(2).replace(' ', '')
        l, w, mat_raw = float(l_raw), float(w_raw), m1.group(3)
        h_raw = m1.group(4).replace(' ', '').strip()
        h = float(h_raw)
        mat = mat_map(mat_raw)
        l, w = max(l, w), min(l, w)
        ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', mat)
        dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-{mat}'
        parsed = True
    
    # ② 长*宽【L*W】cm；外尺寸材料；【【Hcm高】（可能有双括号）
    if not parsed:
        m2 = re.search(r'长\*宽【([\d.]+)\*([\d.]+)】[^；;]*[；;]外尺寸([^；;]*?)[；;]【?【?([\d.]+)cm高】?】?', spec_name)
        if m2:
            l, w, mat_raw, h_raw = float(m2.group(1)), float(m2.group(2)), m2.group(3), float(m2.group(4))
            mat = mat_map(mat_raw)
            l, w = max(l, w), min(l, w)
            ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h_raw), '外径', mat)
            dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h_raw)}-外径-{mat}'
            parsed = True
    
    # ③ 宽高W*H (材料);长 Lcm S5级硬度
    if not parsed:
        m3 = re.search(r'宽高(\d+)\*(\d+)\s*[（(]([^）)]+)[）)];长\s*(\d+)\s*cm', spec_name)
        if m3:
            w, h = int(m3.group(1)), int(m3.group(2))
            mat_raw = m3.group(3)
            l_val = int(m3.group(4))
            mat = mat_map(mat_raw)
            dims = sorted([l_val, w, h], reverse=True)
            ret_code = match_3d(dims[0], dims[1], dims[2], '外径', mat)
            dims_out = f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-外径-{mat}'
            parsed = True
    
    if parsed:
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['匹配'] = stats.get('匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['无匹配'] = stats.get('无匹配', 0) + 1
        continue
    
    # ===== ④ 内寸类: 长*宽【L*W】；内寸材料；Hcm高 =====
    m4 = re.search(r'长\*宽【([\d.]+)\*([\d.]+)】[^；;]*[；;]内寸([^；;]*?)[；;](?:【|)([\d.]+)cm高(?:】|)', spec_name)
    if m4:
        l, w, mat_raw, h_raw = float(m4.group(1)), float(m4.group(2)), m4.group(3), float(m4.group(4))
        mat = mat_map(mat_raw)
        l, w = max(l, w), min(l, w)
        ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h_raw), '内径', mat)
        dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h_raw)}-内径-{mat}'
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['④内寸-匹配'] = stats.get('④内寸-匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['④内寸-无匹配'] = stats.get('④内寸-无匹配', 0) + 1
        continue
    
    # ===== ⑤ 外尺寸【长*宽】L*W;【高】Hcm 材料 =====
    m5 = re.search(r'外尺寸【长\*宽】([\d.]+)\*([\d.]+);【高】([\d.]+)cm\s*(.*?)(?:;|$)', spec_name)
    if m5:
        l, w, h, mat_raw = float(m5.group(1)), float(m5.group(2)), float(m5.group(3)), m5.group(4)
        mat = mat_map(mat_raw)
        l, w = max(l, w), min(l, w)
        ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', mat)
        dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-{mat}'
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['⑤外尺寸L*W-匹配'] = stats.get('⑤外尺寸L*W-匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['⑤外尺寸L*W-无匹配'] = stats.get('⑤外尺寸L*W-无匹配', 0) + 1
        continue
    
    # ===== ⑤b 外尺寸5级特硬原色；【外尺寸】【Hcm高】材料 =====
    m5b = re.search(r'长\*宽【([\d.]+)\*([\d.]+)】[^；;]*[；;]外尺寸[^；;]*[；;]【外尺寸】【([\d.]+)cm高】\s*([^;]*?)(?:;|$)', spec_name)
    if m5b:
        l, w, h, mat_raw = float(m5b.group(1)), float(m5b.group(2)), float(m5b.group(3)), m5b.group(4)
        mat = mat_map(mat_raw)
        l, w = max(l, w), min(l, w)
        ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h), '外径', mat)
        dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h)}-外径-{mat}'
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['⑤b外尺寸双【】-匹配'] = stats.get('⑤b外尺寸双【】-匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['⑤b外尺寸双【】-无匹配'] = stats.get('⑤b外尺寸双【】-无匹配', 0) + 1
        continue
    
    # ===== ⑥ 材料【长*宽】W*H;【高】Hcm  100个一组 =====
    m6 = re.search(r'(.+?)【长\*宽】([\d.]+)\*([\d.]+);【高】([\d.]+)cm', spec_name)
    if m6:
        mat_raw, w, h, h_val = m6.group(1), float(m6.group(2)), float(m6.group(3)), float(m6.group(4))
        mat = mat_map(mat_raw)
        l, w_val = max(w, h), min(w, h)
        ret_code = match_3d(dfmt(l), dfmt(h_val), dfmt(w_val), '外径', mat)
        dims_out = f'{dfmt(l)}*{dfmt(h_val)}*{dfmt(w_val)}-外径-{mat}'
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['⑥材料L*W-匹配'] = stats.get('⑥材料L*W-匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['⑥材料L*W-无匹配'] = stats.get('⑥材料L*W-无匹配', 0) + 1
        continue
    
    # ===== ⑦ 长*宽【L*W】；外尺寸材料；【H高】无cm =====
    m7 = re.search(r'长\*宽【([\d.]+)\*([\d.]+)】[^；;]*[；;]外尺寸([^；;]*?)[；;]【([\d.]+)高】', spec_name)
    if m7:
        l, w, mat_raw, h_raw = float(m7.group(1)), float(m7.group(2)), m7.group(3), float(m7.group(4))
        mat = mat_map(mat_raw)
        l, w = max(l, w), min(l, w)
        ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h_raw), '外径', mat)
        dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h_raw)}-外径-{mat}'
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['⑦外尺寸高-匹配'] = stats.get('⑦外尺寸高-匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['⑦外尺寸高-无匹配'] = stats.get('⑦外尺寸高-无匹配', 0) + 1
        continue
    
    # ===== ⑧ 长*宽【L*Wcm；外尺寸材料；【Hcm高】（缺右括号） =====
    m8 = re.search(r'长\*宽【([\d.]+)\*([\d.]+)cm[^；;]*[；;]外尺寸([^；;]*?)[；;]【([\d.]+)cm高】', spec_name)
    if m8:
        l, w, mat_raw, h_raw = float(m8.group(1)), float(m8.group(2)), m8.group(3), float(m8.group(4))
        mat = mat_map(mat_raw)
        l, w = max(l, w), min(l, w)
        ret_code = match_3d(dfmt(l), dfmt(w), dfmt(h_raw), '外径', mat)
        dims_out = f'{dfmt(l)}*{dfmt(w)}*{dfmt(h_raw)}-外径-{mat}'
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['⑧外尺寸缺]-匹配'] = stats.get('⑧外尺寸缺]-匹配', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['⑧外尺寸缺]-无匹配'] = stats.get('⑧外尺寸缺]-无匹配', 0) + 1
        continue
    
    stats['未识别'] = stats.get('未识别', 0) + 1
    
    if (idx + 1) % 2000 == 0:
        print(f'  已处理 {idx+1}/{len(target)}...')

print('\n=== 统计 ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')
print(f'\n匹配成功: {len(matched_new)}')
print(f'无匹配: {len(nomatch_new)}')
print(f'未识别: {stats.get("未识别", 0)}')

# 写换绑文件
if matched_new:
    batch = 1
    flist = [f for f in os.listdir(OUT_DIR) if f.startswith('换绑文件_第') and f.endswith('.xlsx') and '部分' not in f]
    if flist:
        nums = [int(re.search(r'第(\d+)批', f).group(1)) for f in flist if re.search(r'第(\d+)批', f)]
        batch = max(nums) + 1 if nums else 1
    fname = os.path.join(OUT_DIR, f'换绑文件_第{batch}批.xlsx')
    df_out = pd.DataFrame(matched_new, columns=['店铺名称', '平台商品id', '平台规格id', '商品编码'])
    df_out.to_excel(fname, index=False)
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

# 写无匹配
if nomatch_new:
    rows_to_add = [r for r in nomatch_new if r[3] not in nomatched_existing]
    if rows_to_add:
        if os.path.exists(nm_path):
            df_nm = pd.read_excel(nm_path)
            df_new = pd.DataFrame(rows_to_add, columns=['店铺简称', '平台商品id', '规格名称', '平台规格id', '标记', '尝试解析'])
            pd.concat([df_nm, df_new], ignore_index=True).to_excel(nm_path, index=False)
        else:
            pd.DataFrame(rows_to_add, columns=['店铺简称', '平台商品id', '规格名称', '平台规格id', '标记', '尝试解析']).to_excel(nm_path, index=False)
        print(f'✅ 追加{len(rows_to_add)}条到无匹配')

# 更新平卡
processed_ids = {r[2] for r in matched_new} | {r[3] for r in nomatch_new}
mask_keep = ~df['平台规格id'].astype(str).isin(processed_ids)
df_keep = df[mask_keep]
df_keep.to_excel(PINGKA, index=False)
print(f'✅ 平卡已更新: {len(df_keep)}条')
