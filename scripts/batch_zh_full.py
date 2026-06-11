# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'D:\Desktop\换绑输出'

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
    if not m: return '\u65e0\u8272'
    m = m.strip()
    if '\u96d9\u9762\u8d85\u786c\u767d' in m or '\u96d9\u9762\u767d' in m: return '\u767d\u8272'
    if '\u767d\u8272' in m or '\u767d' == m: return '\u767d\u8272'
    if '\u8d85\u786c\u767d' in m: return '\u767d\u8272'
    if '\u7279\u786c' in m or '\u7279\u4ef7' in m or '\u7279\u60e0' in m: return '\u7279\u786c'
    if '\u725b\u76ae\u7279\u786c' in m or '\u725b\u76ae' in m: return '\u7279\u786c'
    if '\u539f\u8272' in m: return '\u7279\u786c'
    if '\u8d85\u786c' in m: return '\u8d85\u786c'
    if '\u7279\u597d' in m: return '\u4f18\u8d28'
    if '\u4f18\u8d28' in m: return '\u4f18\u8d28'
    if '\u53f0\u6e7e' in m: return '\u8d85\u786c'
    return m.strip()

# ==========================================
# 止合处理规则（平卡中直接读取）
# ==========================================
def parse_zh(s):
    s = s.strip()
    
    # === 1. 扣底盒: 【E坑高度Hcm】材料;3层;扣底盒【长X宽LxW】n个一组 ===
    # 【E坑高度11cm】双面超硬白;3层;扣底盒【长X宽15X15】20个一组
    # -> L=15, W=15, H=11, \u6263\u5e95\u76d2, \u5916\u5f84
    m = re.search(r'\u3010E\u5751\u9ad8\u5ea6(\d+)cm\u3011(.+?)[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u6263\u5e95\u76d2\u3010\u957fX\u5bbd(\d+)X(\d+)\u3011', s)
    if m:
        h, l, w = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mat_raw = m.group(2)
        dk = '\u6263\u5e95\u76d2'
        # \u7279\u786c\u539f\u8272 -> P6D
        if '\u7279\u786c' in mat_raw or '\u725b\u76ae' in mat_raw or '\u539f\u8272' in mat_raw:
            mat = 'P6D'
        else:
            mat = mat_map(mat_raw)
        return (mat, sorted([l, w, h], reverse=True), dk)
    
    # === 2. 飞机盒: 飞机盒【长度Lcm】【材料单个装】;层数;【宽度Wcm】X【高度Hcm】 ===
    # 飞机盒【长度41CM】【特硬单个装】;3层;【宽度8CM】X【高度7CM】
    m = re.search(r'\u98de\u673a\u76d2\u3010\u957f\u5ea6(\d+)cm\u3011\u3010(.+?)\u5355\u4e2a\u88c5\u3011[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u3010\u5bbd\u5ea6(\d+)cm\u3011\s*X\s*\u3010\u9ad8\u5ea6(\d+)cm\u3011', s, re.I)
    if m:
        l, w, h = int(m.group(1)), int(m.group(3)), int(m.group(4))
        return (mat_map(m.group(2)), sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    # === 3. 飞机盒【长度Lcm】外径n个一组;层数;【宽度Wcm】X【高度Hcm】 ===
    m = re.search(r'\u98de\u673a\u76d2\u3010\u957f\u5ea6(\d+)cm\u3011\u5916\u5f84\d+\u4e2a\u4e00\u7ec4[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u3010\u5bbd\u5ea6(\d+)cm\u3011\s*X\s*\u3010\u9ad8\u5ea6(\d+)cm\u3011', s, re.I)
    if m:
        l, w, h = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return ('\u7279\u786c', sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    # === 4. 信封专用/纸专用: X号信封专用【L*W*H】内高x;材料/n个一组 ===
    # 10号信封专用【26*11*2】内高1.5;特惠-特价-特好/100个一组
    m = re.search(r'\u4fe1\u5c01\u4e13\u7528\u3010(\d+)\*(\d+)\*(\d+)\u3011', s)
    if m:
        l, w, h = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return ('\u4f18\u8d28', sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    # === 5. A4纸专用【L*W*H】内高x;材料/n个一组 ===
    # A4纸专用【31.5*21.5*10.5】内高10;特惠-特价-特好/100个一组
    m = re.search(r'A4\u7eb8\u4e13\u7528\u3010([\d.]+)\*([\d.]+)\*([\d.]+)\u3011', s)
    if m:
        l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
        # \u7528\u6237\u8bf4\u7684\u662f30*21*10\u5185\u5f84\uff0c\u4f46\u539f\u6587\u662f31.5*21.5*10.5,\u53d6\u6574
        return ('\u4f18\u8d28', sorted([round(l), round(w), round(h)], reverse=True), '\u5185\u5f84')
    
    # === 6. 纸箱: 纸箱【高度Hcm】/n个一组;层数;纸箱外径/长x宽【LxWcm】 ===
    # 纸箱【高度11cm】/10个一组;5层;纸箱外径-/长x宽【15x15cm】
    m = re.search(r'\u7eb8\u7bb1\u3010\u9ad8\u5ea6(\d+)cm\u3011/\d+\u4e2a\u4e00\u7ec4[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u7eb8\u7bb1\u5916\u5f84[^；;]*\u957fx\u5bbd\u3010([\d.]+)x([\d.]+)cm\u3011', s)
    if m:
        h, l, w = int(m.group(1)), float(m.group(2)), float(m.group(3))
        return ('EB', sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    # === 7. 宽【Wcm】高【Hcm】内径;【n个】长【Lcm】 ===
    m = re.search(r'\u5bbd\u3010(\d+)cm\u3011\u9ad8\u3010(\d+)cm\u3011\u5185\u5f84[^；;]*[；;]\u3010\d+\u4e2a\u3011\u957f\u3010(\d+)cm\u3011', s)
    if m:
        w, h, l = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return ('\u7279\u786c', sorted([l, w, h], reverse=True), '\u5185\u5f84')
    
    # === 8. 5级进口特硬-/宽*高【W*Hcm】;层数;飞机盒长度【Lcm】/n个一捆 ===
    m = re.search(r'/\u5bbd\*\u9ad8\u3010([\d.]+)\*([\d.]+)cm\u3011[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u98de\u673a\u76d2\u957f\u5ea6\u3010(\d+)cm\u3011', s)
    if m:
        w, h, l = float(m.group(1)), float(m.group(2)), int(m.group(3))
        return ('\u767d\u8272', sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    # 同上但带颜色标记
    m = re.search(r'/\u5bbd\*\u9ad8\u3010([\d.]+)\*([\d.]+)cm\u3011[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u98de\u673a\u76d2\u957f\u5ea6\u3010(\d+)cm\u3011/\d+\u4e2a\u4e00\u6346[^；;]*[；;](.+?)\u3010(.+?)\u3011', s)
    if m:
        w, h, l = float(m.group(1)), float(m.group(2)), int(m.group(3))
        return (mat_map(m.group(5)), sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    return None


# ===== \u8bfb\u53d6\u5e73\u5361\uff0c\u5904\u7406\u6b62\u5408 =====
pingka = os.path.join(OUT_DIR, '\u5e73\u5361_\u5f85\u5904\u7406.xlsx')
df = pd.read_excel(pingka)
mask = df['\u5e97\u94fa\u7b80\u79f0'].str.contains('\u6b62\u5408', na=False)
zh = df[mask].copy()
print(f'\u5929\u732b\u6b62\u5408\u5728\u5e73\u5361: {len(zh)} \u6761')

nomatched_existing = set()
nm_path = os.path.join(OUT_DIR, '\u65e0\u5339\u914d_5f85\u5904\u7406.xlsx')
if os.path.exists(nm_path):
    df_nm = pd.read_excel(nm_path)
    nomatched_existing = set(df_nm['\u5e73\u53f0\u89c4\u683cid'].dropna().astype(str).str.strip())

matched_new = []
nomatch_new = []
stats = {}
SHOP_FULL = '\u98de\u673a\u76d2\u6b62\u5408\u4e13\u5356\u5e97'

for idx, (_, row) in enumerate(zh.iterrows()):
    pid = str(row['\u5e73\u53f0\u5546\u54c1id']).strip()
    spec_id = str(row['\u5e73\u53f0\u89c4\u683cid']).strip()
    spec_name = str(row['\u89c4\u683c\u540d\u79f0']).strip()
    shop = str(row['\u5e97\u94fa\u7b80\u79f0']).strip()
    
    if spec_id in nomatched_existing: continue
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
print(f'\n\u5339\u914d\u6210\u529f: {len(matched_new)}')
print(f'\u65e0\u5339\u914d: {len(nomatch_new)}')

if matched_new:
    # \u627e\u51faOK\u6587\u4ef6\u6700\u5927\u6279\u6b21
    import glob
    okdir = r'D:\Desktop\换绑输出\OK文件'
    existing = [int(re.search(r'\u7b2c(\d+)\u6279', f).group(1)) for f in os.listdir(okdir) 
                if f.startswith('\u6362\u7ed1\u6587\u4ef6_\u7b2c') and f.endswith('.xlsx') and '\u90e8\u5206' not in f
                and re.search(r'\u7b2c(\d+)\u6279', f)]
    batch = max(existing) + 1 if existing else 40
    
    fname = os.path.join(okdir, f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{batch}\u6279.xlsx')
    pd.DataFrame(matched_new, columns=['\u5e97\u94fa\u540d\u79f0', '\u5e73\u53f0\u5546\u54c1id', '\u5e73\u53f0\u89c4\u683cid', '\u5546\u54c1\u7f16\u7801']).to_excel(fname, index=False)
    # \u52a0\u6807\u9898\u884c
    import openpyxl
    wb = openpyxl.load_workbook(fname)
    ws = wb.active
    ws.insert_rows(1)
    ws.cell(1, 2).value = '\u5546\u54c1\u5bf9\u5e94\u8868'
    wb.save(fname)
    print(f'\u2705 \u6362\u7ed1\u6587\u4ef6_\u7b2c{batch}\u6279: {len(matched_new)}\u6761')

if nomatch_new:
    rows_to_add = [r for r in nomatch_new if r[3] not in nomatched_existing]
    if rows_to_add:
        if os.path.exists(nm_path):
            df_nm = pd.read_excel(nm_path)
            pd.concat([df_nm, pd.DataFrame(rows_to_add, columns=['\u5e97\u94fa\u7b80\u79f0', '\u5e73\u53f0\u5546\u54c1id', '\u89c4\u683c\u540d\u79f0', '\u5e73\u53f0\u89c4\u683cid', '\u6807\u8bb0', '\u5c1d\u8bd5\u89e3\u6790'])], ignore_index=True).to_excel(nm_path, index=False)
        else:
            pd.DataFrame(rows_to_add, columns=['\u5e97\u94fa\u7b80\u79f0', '\u5e73\u53f0\u5546\u54c1id', '\u89c4\u683c\u540d\u79f0', '\u5e73\u53f0\u89c4\u683cid', '\u6807\u8bb0', '\u5c1d\u8bd5\u89e3\u6790']).to_excel(nm_path, index=False)
        print(f'\u2705 \u8ffd\u52a0{len(rows_to_add)}\u6761\u5230\u65e0\u5339\u914d')

# \u66f4\u65b0\u5e73\u5361
processed_ids = {r[2] for r in matched_new} | {r[3] for r in nomatch_new}
mask_keep = ~df['\u5e73\u53f0\u89c4\u683cid'].astype(str).isin(processed_ids)
df[mask_keep].to_excel(pingka, index=False)
print(f'\u2705 \u5e73\u5361\u5df2\u66f4\u65b0: \u5269\u4f59{df[mask_keep][df[mask_keep]["\u5e97\u94fa\u7b80\u79f0"].str.contains("\u6b62\u5408", na=False)].shape[0]}\u6761')
