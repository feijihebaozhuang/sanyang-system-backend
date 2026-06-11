# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'D:\Desktop\换绑输出'
nm_path = os.path.join(OUT_DIR, '\u65e0\u5339\u914d_5f85\u5904\u7406.xlsx')

km = pd.read_excel(r'D:\Desktop\快麦商品 - 副本.xlsx', sheet_name='\u62a5\u88681', header=3, dtype=str, usecols=[0])
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
    
    # === 1. 飞机盒【长度Lcm】外径n个一组;3层;【宽度Wcm】X【高度Hcm】 ===
    m = re.search(r'\u98de\u673a\u76d2\u3010\u957f\u5ea6(\d+)cm\u3011\u5916\u5f84\d+\u4e2a\u4e00\u7ec4[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u3010\u5bbd\u5ea6(\d+)cm\u3011\s*X\s*\u3010\u9ad8\u5ea6(\d+)cm\u3011', s, re.I)
    if m: return ('\u7279\u786c', sorted([int(m.group(1)), int(m.group(2)), int(m.group(3))], reverse=True), '\u5916\u5f84')
    
    # === 2. 飞机盒【长度Lcm】【特硬单个装/50个一捆】;3层;【宽度Wcm】X【高度Hcm】 ===
    m = re.search(r'\u98de\u673a\u76d2\u3010\u957f\u5ea6(\d+)cm\u3011\u3010[^\u3011]+\u3011[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u3010\u5bbd\u5ea6(\d+)cm\u3011\s*X\s*\u3010\u9ad8\u5ea6(\d+)cm\u3011', s, re.I)
    if m: return ('\u7279\u786c', sorted([int(m.group(1)), int(m.group(2)), int(m.group(3))], reverse=True), '\u5916\u5f84')
    
    # === 3. 5级进口特硬-/宽*高【W*Hcm】;3层;飞机盒长度【Lcm】/n个一捆;特硬【颜色】 ===
    m = re.search(r'/\u5bbd\*\u9ad8\u3010([\d.]+)\*([\d.]+)cm\u3011[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u98de\u673a\u76d2\u957f\u5ea6\u3010(\d+)cm\u3011', s)
    if m:
        w, h, l = float(m.group(1)), float(m.group(2)), int(m.group(3))
        mat = '\u767d\u8272'
        if '\u53cc\u9762\u7ea2' in s or '\u53cc\u9762\u7ea2' in s: mat = '\u7279\u786c'
        elif '\u53cc\u9762\u9ed1' in s or '\u53cc\u9762\u9ed1' in s: mat = '\u7279\u786c'
        elif '\u53cc\u9762\u767d' in s: mat = '\u767d\u8272'
        return (mat, sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    # === 4. 【E坑高度Hcm】材料;3层;扣底盒【长X宽LxW】n个一组 ===
    m = re.search(r'\u3010E\u5751\u9ad8\u5ea6(\d+)cm\u3011(.+?)[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u6263\u5e95\u76d2\u3010\u957fX\u5bbd(\d+)X(\d+)\u3011', s)
    if m:
        h, l, w = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mat_raw = m.group(2)
        if '\u725b\u76ae\u7279\u786c\u539f\u8272' in mat_raw: mat = 'P6D'
        elif '\u53cc\u9762\u8d85\u786c\u767d' in mat_raw: mat = '\u767d\u8272'
        else: mat = '\u767d\u8272'
        return (mat, sorted([l, w, h], reverse=True), '\u6263\u5e95\u76d2')
    
    # === 5. X号信封专用【L*W*H】内高x;材料/n个一组 ===
    m = re.search(r'\u4fe1\u5c01\u4e13\u7528\u3010(\d+)\*(\d+)\*(\d+)\u3011', s)
    if m: return ('\u4f18\u8d28', sorted([int(m.group(1)), int(m.group(2)), int(m.group(3))], reverse=True), '\u5916\u5f84')
    
    # === 6. A4纸专用【L*W*H】内高x;材料/n个一组 ===
    m = re.search(r'A4\u7eb8\u4e13\u7528\u3010([\d.]+)\*([\d.]+)\*([\d.]+)\u3011', s)
    if m: return ('\u4f18\u8d28', sorted([round(float(m.group(1))), round(float(m.group(2))), round(float(m.group(3)))], reverse=True), '\u5185\u5f84')
    
    # === 7. 纸箱【高度Hcm】/n个一组;5层;纸箱外径-/长x宽【LxWcm】 ===
    m = re.search(r'\u7eb8\u7bb1\u3010\u9ad8\u5ea6(\d+)cm\u3011/\d+\u4e2a\u4e00\u7ec4[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u7eb8\u7bb1\u5916\u5f84[^；;]*\u957fx\u5bbd\u3010([\d.]+)x([\d.]+)cm\u3011', s)
    if m: return ('EB', sorted([float(m.group(2)), float(m.group(3)), int(m.group(1))], reverse=True), '\u5916\u5f84')
    
    # === 8. 宽【Wcm】高【Hcm】内径;【n个】长【Lcm】 ===
    m = re.search(r'\u5bbd\u3010(\d+)cm\u3011\u9ad8\u3010(\d+)cm\u3011\u5185\u5f84[^；;]*[；;]\u3010\d+\u4e2a\u3011\u957f\u3010(\d+)cm\u3011', s)
    if m: return ('\u7279\u786c', sorted([int(m.group(3)), int(m.group(1)), int(m.group(2))], reverse=True), '\u5185\u5f84')
    
    return None

# 读无匹配_待处理，只处理止合
df_nm = pd.read_excel(nm_path)
mask = df_nm['\u5e97\u94fa\u7b80\u79f0'].str.contains('\u6b62\u5408', na=False)
zh = df_nm[mask].copy().reset_index(drop=True)
print(f'\u5929\u732b\u6b62\u5408\u5728\u65e0\u5339\u914d\u4e2d: {len(zh)} \u6761')

matched_new = []
nomatch_new = []
stats = {}
SHOP_FULL = '\u98de\u673a\u76d2\u6b62\u5408\u4e13\u5356\u5e97'

for idx, (_, row) in enumerate(zh.iterrows()):
    pid = str(row['\u5e73\u53f0\u5546\u54c1id']).strip()
    spec_id = str(row['\u5e73\u53f0\u89c4\u683cid']).strip()
    spec_name = str(row['\u89c4\u683c\u540d\u79f0']).strip()
    shop = str(row['\u5e97\u94fa\u7b80\u79f0']).strip()
    
    result = parse_zh(spec_name)
    
    if result and result[1][0] is not None:
        mat, dims, dk = result
        ret_code = match_3d(dfmt(dims[0]), dfmt(dims[1]), dfmt(dims[2]), dk, mat)
        dims_out = f'{dfmt(dims[0])}*{dfmt(dims[1])}*{dfmt(dims[2])}-{dk}-{mat}'
        
        if ret_code:
            matched_new.append((SHOP_FULL, pid, spec_id, ret_code))
            stats['\u5339\u914d'] = stats.get('\u5339\u914d', 0) + 1
        else:
            nomatch_new.append((shop, pid, spec_name, spec_id, '\u65e0\u5339\u914d', dims_out))
            stats['\u65e0\u5339\u914d'] = stats.get('\u65e0\u5339\u914d', 0) + 1
    else:
        stats['\u672a\u8bc6\u522b'] = stats.get('\u672a\u8bc6\u522b', 0) + 1
        if stats['\u672a\u8bc6\u522b'] <= 5:
            print(f'  \u672a\u8bc6\u522b: {spec_name[:60]}')

print('\n=== \u7edf\u8ba1 ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')
print(f'\u5339\u914d\u6210\u529f: {len(matched_new)}')
print(f'\u65e0\u5339\u914d: {len(nomatch_new)}')

if matched_new:
    okdir = r'D:\Desktop\换绑输出\OK文件'
    existing = sorted([int(re.search(r'\u7b2c(\d+)\u6279', f).group(1)) for f in os.listdir(okdir) 
                if f.startswith('\u6362\u7ed1\u6587\u4ef6_\u7b2c') and f.endswith('.xlsx') and '\u90e8\u5206' not in f
                and re.search(r'\u7b2c(\d+)\u6279', f)])
    batch = max(existing) + 1 if existing else 40
    
    fname = os.path.join(okdir, f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{batch}\u6279.xlsx')
    pd.DataFrame(matched_new, columns=['\u5e97\u94fa\u540d\u79f0', '\u5e73\u53f0\u5546\u54c1id', '\u5e73\u53f0\u89c4\u683cid', '\u5546\u54c1\u7f16\u7801']).to_excel(fname, index=False)
    import openpyxl
    wb = openpyxl.load_workbook(fname)
    ws = wb.active
    ws.insert_rows(1)
    ws.cell(1, 2).value = '\u5546\u54c1\u5bf9\u5e94\u8868'
    wb.save(fname)
    print(f'\u2705 \u6362\u7ed1\u6587\u4ef6_\u7b2c{batch}\u6279: {len(matched_new)}\u6761')

# 从无匹配中删除止合已处理的
zh_processed = set(zh['\u5e73\u53f0\u89c4\u683cid'].dropna().astype(str).str.strip())
mask_keep = ~df_nm['\u5e73\u53f0\u89c4\u683cid'].astype(str).isin(zh_processed)
left = df_nm[mask_keep]
left.to_excel(nm_path, index=False)
print(f'\u2705 \u65e0\u5339\u914d\u5df2\u66f4\u65b0: \u5269\u4f59{len(left)}\u6761')
