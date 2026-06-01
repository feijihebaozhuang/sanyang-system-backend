# -*- coding: utf-8 -*-
"""
天猫止合专用处理脚本
处理6种格式：
1. 飞机盒【长度Lcm】外径n个一组;3层;【宽度Wcm】X【高度Hcm】 → 外径/特硬【L*W*H】
2. 飞机盒【长度Lcm】【XX】;3层;【宽度Wcm】X【高度Hcm】 → 外径/特硬【L*W*H】
3. 5级进口特硬-/宽*高【W*Hcm】;3层;飞机盒长度【Lcm】/n个一捆;特硬【颜色】 → 外径/颜色【L*W*H】
4. 【E坑高度Hcm】材料;3层;扣底盒【长X宽LxW】n个一组 → 扣底盒/白或P6D【L*W*H】
5. X号信封专用【L*W*H】或A4纸专用【L*W*H】 → 外径或内径/优质
6. 纸箱【高度Hcm】/n个一组;5层;纸箱外径-/长x宽【LxWcm】 → 外径/EB【L*W*H】
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'D:\Desktop\换绑输出'
nm_path = os.path.join(OUT_DIR, '无匹配_待处理.xlsx')

# ===== 快麦商品映射 =====
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
    """返回 (mat, [L, W, H]从大到小, dk) 或 None"""
    s = s.strip()
    
    # ============ 格式1: 飞机盒【长度Lcm】外径n个一组;3层;【宽度Wcm】X【高度Hcm】 ============
    # 例: 飞机盒【长度39CM】外径100个一组;3层;【宽度8CM】X【高度8CM】
    m = re.search(r'飞机盒【长度(\d+)C?M?】外径\d+个一组;(\d+)层;【宽度(\d+)C?M?】\s*X\s*【高度(\d+)C?M?】', s)
    if m: return ('特硬', sorted([int(m.group(1)), int(m.group(3)), int(m.group(4))], reverse=True), '外径')
    
    # ============ 格式2: 飞机盒【长度Lcm】【XX】;层;【宽度Wcm】X【高度Hcm】 ============
    # 例: 飞机盒【长度41CM】【特硬单个装】;3层;【宽度8CM】X【高度7CM】
    # 例: 飞机盒【长度41CM】【50个一捆】;3层;【宽度10CM】X【高度5CM】
    m = re.search(r'飞机盒【长度(\d+)C?M?】【[^】]+】;(\d+)层;【宽度(\d+)C?M?】\s*X\s*【高度(\d+)C?M?】', s)
    if m: return ('特硬', sorted([int(m.group(1)), int(m.group(3)), int(m.group(4))], reverse=True), '外径')
    
    # ============ 格式3: 5级进口特硬-/宽*高【W*Hcm】;层;飞机盒长度【Lcm】/n个一捆;特硬【颜色】 ============
    # 例: 5级进口特硬-/宽*高【10*10cm】;3层;飞机盒长度【41cm】/100个一捆;特硬【双面白】
    # 例: 5级进口特硬-/宽*高【10*10cm】;3层;飞机盒长度【41cm】/100个一捆;特硬【双面红】
    # 例: 5级进口特硬-/宽*高【10*10cm】;3层;飞机盒长度【41cm】/100个一捆;特硬【双面黑】
    m = re.search(r'/宽\*高【([\d.]+)\*([\d.]+)c?m?】;(\d+)层;飞机盒长度【(\d+)c?m?】', s)
    if m:
        wh, hh, l = float(m.group(1)), float(m.group(2)), int(m.group(4))
        # 颜色：最后特硬【颜色】
        color = '特硬'
        if '双面红' in s: color = '特硬'
        elif '双面黑' in s: color = '特硬'
        elif '双面白' in s: color = '白色'
        return (color, sorted([l, wh, hh], reverse=True), '外径')
    
    # ============ 格式4: 【E坑高度Hcm】材料;层;扣底盒【长X宽LxW】n个一组 ============
    # 例: 【E坑高度11cm】双面超硬白;3层;扣底盒【长X宽15X15】20个一组 → 白色/扣底盒
    # 例: 【E坑高度11cm】牛皮特硬原色;3层;扣底盒【长X宽15X15】20个一组 → P6D/扣底盒
    m = re.search(r'【E坑高度(\d+)c?m?】(.+?);(\d+)层;扣底盒【长X宽(\d+)X(\d+)】', s)
    if m:
        h, l, w = int(m.group(1)), int(m.group(4)), int(m.group(5))
        mat_raw = m.group(2)
        if '牛皮特硬原色' in mat_raw: mat = 'P6D'
        else: mat = '白色'
        return (mat, sorted([l, w, h], reverse=True), '扣底盒')
    
    # ============ 格式5a: X号信封专用【L*W*H】 或 C5信封专用【L*W*H】 ============
    # 例: 10号信封专用【26*11*2】内高1.5;特惠-特价-特好/100个一组
    # 例: C5信封专用【23.5*16.5*2.5】内高2;特惠-特价-特好/100个一组
    m = re.search(r'信封专用【([\d.]+)\*([\d.]+)\*([\d.]+)】', s)
    if m:
        l = float(m.group(1)); w = float(m.group(2)); h = float(m.group(3))
        return ('优质', sorted([round(l), round(w), round(h)], reverse=True), '外径')
    
    # ============ 格式5b: A4纸专用【L*W*H】 -> 内径 ============
    # 例: A4纸专用【31.5*21.5*10.5】内高10;特惠-特价-特好/100个一组
    m = re.search(r'A4纸专用【([\d.]+)\*([\d.]+)\*([\d.]+)】', s)
    if m: return ('优质', sorted([round(float(m.group(1))), round(float(m.group(2))), round(float(m.group(3)))], reverse=True), '内径')
    
    # ============ 格式5c: A编号【L*W*H】;特惠... ============
    # 例: A11【18*13*6.5】;特惠-特价-特好/100个一组
    # 例: A2【13.5*8*3】;特惠-特价-特好/100个一组
    m = re.search(r'^[A-Z]\d+【([\d.]+)\*([\d.]+)\*([\d.]+)】;', s)
    if m:
        l = float(m.group(1)); w = float(m.group(2)); h = float(m.group(3))
        return ('优质', sorted([round(l), round(w), round(h)], reverse=True), '外径')
    
    # ============ 格式6: 纸箱【高度Hcm】/n个一组;层;纸箱外径-/长x宽【LxWcm】 ============
    # 例: 纸箱【高度11cm】-/10个一组;5层;纸箱外径-/长x宽【15x15cm】
    m = re.search(r'纸箱【高度(\d+)c?m?】[^；;]*;(\d+)层;纸箱外径[^；;]*长x宽【([\d.]+)x([\d.]+)c?m?】', s)
    if m: return ('EB', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '外径')
    
    return None


# ===== 主处理流程 =====
# 1. 先读取无匹配中的所有止合数据
df_nm = pd.read_excel(nm_path)
mask = df_nm['店铺简称'].str.contains('止合', na=False)
zh = df_nm[mask].copy().reset_index(drop=True)
print(f'天猫止合在无匹配中: {len(zh)} 条')

if len(zh) == 0:
    print('没有止合数据需要处理')
    sys.exit(0)

SHOP_FULL = '飞机盒止合专卖店'
matched_new = []
nomatch_new = []
unrecog = []
stats = {}

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
            stats['匹配成功'] = stats.get('匹配成功', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '无匹配', dims_out))
            stats['解析成功_快麦无匹配'] = stats.get('解析成功_快麦无匹配', 0) + 1
            if stats['解析成功_快麦无匹配'] <= 10:
                print(f'  解析成功无匹配: {dims_out}')
    else:
        unrecog.append((shop, pid, spec_name, spec_id, '未识别', ''))
        stats['未识别'] = stats.get('未识别', 0) + 1
        if stats['未识别'] <= 10:
            print(f'  未识别: {spec_name[:60]}')

print('\n=== 统计 ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')
print(f'匹配成功: {len(matched_new)}')
print(f'解析成功但快麦无此码: {len(nomatch_new)}')
print(f'未识别: {len(unrecog)}')

# 输出匹配成功到换绑文件
if matched_new:
    okdir = r'D:\Desktop\换绑输出\OK文件'
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
    print(f'\n✅ 换绑文件_第{batch}批: {len(matched_new)}条')

# 更新无匹配：移除止合已处理，添加解析成功的和未识别的
# 从原始df中删除所有止合行
non_zh = df_nm[~mask].copy()
# 把解析成功但无匹配、未识别的加到无匹配
rows_to_add = []
for r in nomatch_new:
    rows_to_add.append({
        '店铺简称': r[0], '平台商品id': r[1], '规格名称': r[2],
        '平台规格id': r[3], '标记': r[4], '尝试解析': r[5]
    })
for r in unrecog:
    rows_to_add.append({
        '店铺简称': r[0], '平台商品id': r[1], '规格名称': r[2],
        '平台规格id': r[3], '标记': r[4], '尝试解析': r[5]
    })

if rows_to_add:
    df_new = pd.DataFrame(rows_to_add)
    combined = pd.concat([non_zh, df_new], ignore_index=True)
else:
    combined = non_zh

combined.to_excel(nm_path, index=False)
print(f'✅ 无匹配已更新: 共{len(combined)}条 (原始{len(df_nm)}条, 移除了{len(zh)}条止合, 回写了{len(rows_to_add)}条解析结果)')
