# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

OUT_DIR = r'D:\Desktop\换绑输出'
nm_path = os.path.join(OUT_DIR, '\u65e0\u5339\u914d_5f85\u5904\u7406.xlsx')
# 用平卡找止合的原始数据
pingka = os.path.join(OUT_DIR, '\u5e73\u5361_\u5f85\u5904\u7406.xlsx')

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

def parse_zh(s):
    """解析天猫止合格式"""
    s = s.strip()
    
    # Z1: 飞机盒【长度Xcm】外径n个一组;层数;【宽度Xcm】X【高度Xcm】
    # 飞机盒【长度39CM】外径100个一组;3层;【宽度8CM】X【高度8CM】
    m = re.search(r'\u98de\u673a\u76d2\u3010\u957f\u5ea6(\d+)CM\u3011\u5916\u5f84\d+\u4e2a\u4e00\u7ec4[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u3010\u5bbd\u5ea6(\d+)CM\u3011\s*X\s*\u3010\u9ad8\u5ea6(\d+)CM\u3011', s)
    if m:
        l, w, h = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return ('\u7279\u786c', sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    # Z2: 5级进口特硬-/宽*高【W*Hcm】;层数;飞机盒长度【Lcm】/n个一捆;材料【颜色】
    # 5级进口特硬-/宽*高【10*10cm】;3层;飞机盒长度【41cm】/100个一捆;特硬【双面白】
    m = re.search(r'[^；;]*?/宽\*高\u3010([\d.]+)\*([\d.]+)cm\u3011[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u98de\u673a\u76d2\u957f\u5ea6\u3010(\d+)cm\u3011/\d+\u4e2a\u4e00\u6346[^；;]*[；;](.+?)\u3010(.+?)\u3011', s)
    if m:
        w, h, l = float(m.group(1)), float(m.group(2)), float(m.group(3))
        mat_color = m.group(5)  # \u96d9\u9762\u767d
        return (mat_map(mat_color), sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    # Z3: 更简化的止合格式：宽*高【W*Hcm】;层;飞机盒长度【Lcm】
    m = re.search(r'\u5bbd\*\u9ad8\u3010([\d.]+)\*([\d.]+)cm\u3011[^；;]*[；;]\d+\u5c42[^；;]*[；;]\u98de\u673a\u76d2\u957f\u5ea6\u3010(\d+)cm\u3011', s)
    if m:
        w, h, l = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return ('\u7279\u786c', sorted([l, w, h], reverse=True), '\u5916\u5f84')
    
    # Z4: 宽【Xcm】高【Xcm】内径;【n个】长【Xcm】
    # 宽【10cm】高【8cm】内径;【100个】长【41cm】
    m = re.search(r'\u5bbd\u3010(\d+)cm\u3011\u9ad8\u3010(\d+)cm\u3011\u5185\u5f84[^；;]*[；;]\u3010\d+\u4e2a\u3011\u957f\u3010(\d+)cm\u3011', s)
    if m:
        w, h, l = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return ('\u7279\u786c', sorted([l, w, h], reverse=True), '\u5185\u5f84')
    
    return None

def mat_map(m):
    if not m: return '\u65e0\u8272'
    m = m.strip().replace('\uff1b','').replace(';','')
    if '\u96d9\u9762\u767d\u8272' in m or '\u96d9\u9762\u767d' in m or '\u7279\u786c\u96d9\u9762\u767d' in m: return '\u767d\u8272'
    if '\u767d\u76d2' in m: return '\u767d\u8272'
    if m == '\u767d\u8272' or m == '\u767d\u8272\u7eb8': return '\u767d\u8272'
    if '\u8d85\u786c\u53f0\u6e7e' in m or '\u53f0\u6e7e\u7eb8\u8d85\u786c' in m or '\u53f0\u6e7e\u9ec4\u8d85\u786c' in m: return '\u8d85\u786c'
    if '\u53f0\u6e7e\u7eb8' in m or '\u53f0\u6e7e\u9ec4' in m: return '\u8d85\u786c'
    if '\u8d85\u786c' in m: return '\u8d85\u786c'
    if '\u8d85\u7ea7' in m: return '\u8d85\u786c'
    if '\u7279\u60e0' in m: return '\u7279\u786c'
    if '\u7279\u786c' in m or '\u7279\u4ef7' in m: return '\u7279\u786c'
    if '\u9ec4\u8272' in m: return '\u7279\u786c'
    if '\u725b\u76ae\u8272' in m or '\u725b\u76ae' in m: return '\u7279\u786c'
    if '\u539f\u8272' in m: return '\u7279\u786c'
    if '\u7389\u9f99' in m or 'S\u7ea7' in m: return '\u7279\u786c'
    if 'E\u5751' in m: return '\u7279\u786c'
    if '\u52a0\u5f3a' in m: return '\u7279\u786c'
    if '\u9ad8\u6863' in m: return '\u7279\u786c'
    if '\u4f18\u8d28' in m: return '\u4f18\u8d28'
    if '\u767d\u8272' in m or '\u767d' in m: return '\u767d\u8272'
    if '\u7ea2\u8272' in m: return '\u7279\u786c'
    return m.strip()

# 从平卡读止合数据
df_pingka = pd.read_excel(pingka)
mask_pingka = df_pingka['\u5e97\u94fa\u7b80\u79f0'].str.contains('\u6b62\u5408', na=False)
zh_pingka = df_pingka[mask_pingka].copy()
print(f'\u5929\u732b\u6b62\u5408\u5728\u5e73\u5361\u4e2d: {len(zh_pingka)} \u6761')

# 检查是否已有部分在无匹配_待处理中
df_nm = pd.read_excel(nm_path)
zh_nm = df_nm[df_nm['\u5e97\u94fa\u7b80\u79f0'].str.contains('\u6b62\u5408', na=False)]
print(f'\u5929\u732b\u6b62\u5408\u5728\u65e0\u5339\u914d\u4e2d: {len(zh_nm)} \u6761')
print(f'\u5e73\u5361\u4e2d\u6b62\u5408\u5171: {len(zh_pingka)}')

# 显示前10条规格
for i, (_, row) in enumerate(zh_pingka.head(10).iterrows()):
    print(f'  {i+1}. {str(row.get("\u89c4\u683c\u540d\u79f0",""))[:80]}')
    parsed = parse_zh(str(row.get("\u89c4\u683c\u540d\u79f0","")))
    print(f'     \u89e3\u6790: {parsed}')
