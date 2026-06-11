# -*- coding: utf-8 -*-
"""友尚v5 - 全面覆盖所有剩余模式"""
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
    
    # ===== F1: LxW cm【长宽】;H cm高【层纸箱】n个 =====
    # 32x31 cm【长宽】;37 cm高【五层纸箱】50个
    m = re.search(r'([\d.]+)x\s*([\d.]+)\s*cm【长宽】[^；;]*[；;](\d+)\s*cm高【(.+?)纸箱】\s*(\d+)个', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # ===== F2: LxW cm【长宽】;高度Hcm【层纸箱】n个（高度带"高度"） =====
    m = re.search(r'([\d.]+)x\s*([\d.]+)\s*cm【长宽】[^；;]*[；;](\d+)\s*cm高', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # ===== F3: LxW cm【长宽】;H cm高【层纸箱】n个（无前缀空格） =====
    m = re.search(r'([\d.]+)x\s*([\d.]+)\s*cm【长宽】[^；;]*[；;](\d+)\s*cm\s*高【', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # ===== F4: LxW cm【长宽】;H cm高【层纸箱】（无纸箱词的通用匹配） =====
    m = re.search(r'([\d.]+)x\s*([\d.]+)\s*cm【长宽】[^；;]*[；;](\d+)\s*cm\s*高', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # ===== F5: 高Hcm【五层】；长宽【L*W】n个 =====
    # 高12cm【五层】；长宽【29*15】;高12cm【五层】;长宽【29*15】
    # 注意有重复数据（分号分隔的重复段），先做spec_clean
    m = re.search(r'高(\d+)cm【\d+层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】', s)
    if m:
        return ('特硬', sorted([float(m.group(2)), float(m.group(3)), int(m.group(1))], reverse=True), '外径')
    
    # ===== F6: 高度Hcm【纸箱】n个;长宽LxWmm（mm单位） =====
    # 高度24cm【五层纸箱】50个;长宽47x37mm
    m = re.search(r'高度(\d+)cm【.+?纸箱】\s*(\d+)个[^；;]*[；;]长宽([\d.]+)x([\d.]+)(mm|cm)', s)
    if m:
        h = int(m.group(1))
        if m.group(5) == 'mm':
            l, w = round(float(m.group(3))/10, 1), round(float(m.group(4))/10, 1)
        else:
            l, w = float(m.group(3)), float(m.group(4))
        return ('特硬', sorted([l, w, h], reverse=True), '内径')
    
    # ===== F7: 高度Hcm【纸箱】n个;长宽LxW（无单位） =====
    m = re.search(r'高度(\d+)cm【.+?纸箱】\s*(\d+)个[^；;]*[；;]长宽([\d.]+)x([\d.]+)', s)
    if m:
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '内径')
    
    # ===== F8: 高度Hcm【纸箱】n个;L*W【长宽mm】或L*Wmm =====
    m = re.search(r'高度(\d+)cm【.+?纸箱】\s*(\d+)个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?', s)
    if m:
        return ('特硬', sorted([int(m.group(3)), int(m.group(4)), int(m.group(1))], reverse=True), '内径')
    
    # ===== F9: 高度Hcm【五层纸箱】n个;L*Wmm（纯数字无标记） =====
    m = re.search(r'高度(\d+)cm【.+?纸箱】\s*(\d+)个[^；;]*[；;](\d+)\*(\d+)(?:\*?)(mm|CM|cm)?', s)
    if m:
        l_mm, w_mm = int(m.group(3)), int(m.group(4))
        if l_mm > 100 and w_mm > 100:  # 很可能是mm
            return ('特硬', sorted([round(l_mm/10,1), round(w_mm/10,1), int(m.group(1))], reverse=True), '内径')
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '内径')
    
    # ===== F10: 高【Hcm】【层纸箱】；长宽【L*Wcm】n个 =====
    # 高【12cm】【三层纸箱】；长宽【30*20cm】100个
    m = re.search(r'高【(\d+)cm】【(.+?纸箱)】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)cm】', s)
    if m:
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '外径')
    
    # ===== F11: 高【Hcm】【层纸箱】；长宽【L*W】n个（无cm后缀） =====
    m = re.search(r'高【(\d+)cm】【(.+?纸箱)】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】', s)
    if m:
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '外径')
    
    # ===== F12: 长x宽【LxW】高+0.5;材料高度【Hcm】 =====
    # 长x宽【11.5x10.5】高度+0.5;台湾纸高度【10厘米】
    m = re.search(r'长x宽【([\d.]+)x([\d.]+)】[^；;]*[；;](.+?)高度【(\d+)厘米】', s)
    if m:
        return (mat_map(m.group(3)), sorted([float(m.group(1)), float(m.group(2)), int(m.group(4))], reverse=True), '外径')
    
    # ===== F13: 长x宽【LxW】高+0.5;高度【Hcm】 =====
    m = re.search(r'长x宽【([\d.]+)x([\d.]+)】[^；;]*[；;]高度【(\d+)厘米】', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # ===== F14: 长【L】cm；宽【W】cm；*材料 =====
    # 长【100】cm；宽【10】cm；三层原色【厚的】
    m = re.search(r'长【(\d+)】cm[^；;]*[；;]宽【(\d+)】cm[^；;]*[；;](.+?)(?:【.*?】)?$', s)
    if m:
        h = 999  # 默认高度
        return (mat_map(m.group(3)), sorted([int(m.group(1)), int(m.group(2)), h], reverse=True), '外径')
    
    # ===== F15: 数量前导*n个材料*LxWxH（n个材料*LxWxH） =====
    # 100个双面白色*10*10*6.5
    m = re.search(r'^(\d+)个(.+?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(2)), sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True), '外径')
    
    # ===== F16: 材料【数量】*LxWxH =====
    # 特硬【白色100个】*18.1x10.9x4.2
    m = re.search(r'^(.+?)【[^】]+】[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(2)), float(m.group(3)), float(m.group(4))], reverse=True), '外径')
    
    # ===== F17: 材料n个/组*LxWxH =====
    # 白色100个*22x10.5x6
    m = re.search(r'^(.+?)(\d+)个[组/]*[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True), '外径')
    
    # ===== F18: 【H厘米高】材料-数量;L*W【长宽】unit（有特殊单位） =====
    m = re.search(r'【(\d+)厘米高】(.+?)-(\d+)个[^；;]*[；;](\d+)\*(\d+)mm【长宽】', s)
    if m:
        return (mat_map(m.group(2)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(1))], reverse=True), '内径')
    
    m = re.search(r'【(\d+)厘米高】(.+?)-(\d+)个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】\s*(?:cm|CM)?(?:【.*?)?(?:;|$)', s)
    if m:
        return (mat_map(m.group(2)), sorted([float(m.group(4)), float(m.group(5)), int(m.group(1))], reverse=True), '内径')
    
    m = re.search(r'【(\d+)厘米高】(.+?)-(\d+)个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】\s*(?:mm|MM)?(?:【.*?)?(?:;|$)', s)
    if m:
        return (mat_map(m.group(2)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(1))], reverse=True), '内径')
    
    # ===== F19: 材料-数量【H厘米高】;L*W单位 =====
    m = re.search(r'(.+?)-(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(mm|MM)?', s)
    if m:
        if m.group(6) in ('mm','MM'):
            return (mat_map(m.group(1)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(3))], reverse=True), '内径')
        return (mat_map(m.group(1)), sorted([float(m.group(4)), float(m.group(5)), int(m.group(3))], reverse=True), '内径')
    
    # ===== F20: 材料-数量【Hmm高】;L*W【长宽mm】 =====
    m = re.search(r'(.+?)-(\d+)个【(\d+)mm高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽mm】?(?:【.*?)?(?:;|$)', s)
    if m:
        return (mat_map(m.group(1)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), round(int(m.group(3))/10,1)], reverse=True), '内径')
    
    # ===== F21: 材料n个【Hmm高】;L*W长宽mm =====
    m = re.search(r'(.+?)(\d+)个【(\d+)mm高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*mm?', s)
    if m:
        return (mat_map(m.group(1)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), round(int(m.group(3))/10,1)], reverse=True), '内径')
    
    # ===== F22: 材料 n个【Hcm高】;L*W【长宽mm】 =====
    m = re.search(r'(.+?)\s+(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(4)), float(m.group(5)), int(m.group(3))], reverse=True), '内径')
    
    # ===== F23: 材料【白色N个】*LxWxH =====
    m = re.search(r'^(.+?)【[^】]+?\d+个[^】]*?】[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(2)), float(m.group(3)), float(m.group(4))], reverse=True), '外径')
    
    # ===== F24: 白色【N个】材料*LxWxH =====
    # 白色【100个】特硬*28.1x12.9x6.9
    m = re.search(r'^(.+?)【(\d+)个】(.+?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(1) + m.group(3)), sorted([float(m.group(4)), float(m.group(5)), float(m.group(6))], reverse=True), '外径')
    
    # ===== F25: 材料-内尺寸【数量】*L*W*H =====
    m = re.search(r'(.+?)(?:内尺寸|内径|内寸).+?【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        return (mat_map(m.group(1)), sorted([int(m.group(3)), int(m.group(4)), int(m.group(5))], reverse=True), '内径')
    
    # ===== F26: 材料外尺寸【数量】*L*W*H =====
    m = re.search(r'(.+?)(?:外尺寸|外径|外寸).+?【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        return (mat_map(m.group(1)), sorted([int(m.group(3)), int(m.group(4)), int(m.group(5))], reverse=True), '外径')
    
    # ===== F27: 特价一组【型号】：L*W*Hcm =====
    m = re.search(r'特价\s+\d+个一组[^；;]*[；;]【[^】]+】[：:]?([\d.]+)\*([\d.]+)\*([\d.]+)cm', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True), '外径')
    
    # ===== F28: L*W*Hcm外径五层纸箱 =====
    m = re.search(r'([\d.]+)\*([\d.]+)\*([\d.]+)cm\s*外径', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True), '外径')
    
    # ===== F29: 长度Hcm---材料-n个组;W*H【宽高】 =====
    m = re.search(r'长度(\d+)cm---(.+?)-(\d+)个[组\]]*[^；;]*[；;](\d+)\*(\d+)【宽高】', s)
    if m:
        return (mat_map(m.group(2)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(1))], reverse=True), '内径')
    
    # ===== F30: 材料【数量】*LxWxH（直接在末尾） =====
    m = re.search(r'(.+?)【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True), '外径')
    
    # ===== F31: 外径【长宽】LxW;高度Hcm【层 纸箱】n个 =====
    m = re.search(r'外径【长宽】([\d.]+)x([\d.]+)[^；;]*[；;]高度(\d+)cm【\d+层\s*纸箱】', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
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
