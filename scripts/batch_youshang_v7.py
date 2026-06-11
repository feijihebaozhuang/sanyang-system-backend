# -*- coding: utf-8 -*-
"""友尚v7 - 终极版本，单次覆盖所有530种格式"""
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
    
    # ===== H0: Hcm高【纸箱】n个;长宽【L*Wcm】 (数字cm高前导, 有空格) =====
    # 37 cm高【五层纸箱】50个;长宽【14*13cm】
    m = re.search(r'(\d+)\s*cm高【(.+?纸箱)】\s*\d+个[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)cm】', s)
    if m:
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '外径')
    
    # 37 cm高【五层纸箱】50个;长宽【14*13】(无cm)
    m = re.search(r'(\d+)\s*cm高【(.+?纸箱)】\s*\d+个[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】', s)
    if m:
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '外径')
    
    # ===== H0b: Hcm高【纸箱】n个;L*W【长宽cm】 (不同排列) =====
    m = re.search(r'(\d+)\s*cm高【(.+?)】\s*\d+个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*cm?', s)
    if m:
        return ('特硬', sorted([int(m.group(3)), int(m.group(4)), int(m.group(1))], reverse=True), '外径')
    
    # ===== H1: 高Hcm【x层】；长宽【L*W】n个 =====
    # 高12cm【五层】；长宽【29*21】100个
    m = re.search(r'高(\d+)cm【(.+?)层[^】]*】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】', s)
    if m:
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '外径')
    
    # ===== H2: 高【Hcm】【层纸箱】；长宽【L*Wcm】 =====
    m = re.search(r'高【(\d+)cm】【(.+?纸箱)】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)cm】', s)
    if m:
        return ('特硬', sorted([float(m.group(3)), float(m.group(4)), int(m.group(1))], reverse=True), '外径')
    
    # ===== H3: 高度Hcm【纸箱】n个;长宽LxWmm =====
    m = re.search(r'高度(\d+)cm【(.+?纸箱)】\s*\d+个[^；;]*[；;]长宽([\d.]+)x([\d.]+)(mm|cm)', s)
    if m:
        h = int(m.group(1))
        l = round(float(m.group(3))/10,1) if m.group(5)=='mm' else float(m.group(3))
        w = round(float(m.group(4))/10,1) if m.group(5)=='mm' else float(m.group(4))
        return ('特硬', sorted([l, w, h], reverse=True), '内径')
    
    # ===== H4: 高度Hcm【纸箱】n个;L*W【长宽】... =====
    m = re.search(r'高度(\d+)cm【(.+?纸箱)】\s*\d+个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?', s)
    if m:
        return ('特硬', sorted([int(m.group(3)), int(m.group(4)), int(m.group(1))], reverse=True), '内径')
    
    # ===== H5: 外径【长宽】LxW;高度Hcm【层纸箱】 =====
    m = re.search(r'外径【长宽】([\d.]+)x([\d.]+)[^；;]*[；;]高度(\d+)cm【\d+层\s*纸箱】', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # ===== H6: LxW cm【长宽】;H cm高【纸箱】 =====
    m = re.search(r'([\d.]+)x\s*([\d.]+)\s*cm【长宽】[^；;]*[；;](\d+)\s*cm高【(.+?纸箱)】', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # ===== H7: LxW cm【长宽】;H cm高（无纸箱） =====
    m = re.search(r'([\d.]+)x\s*([\d.]+)\s*cm【长宽】[^；;]*[；;](\d+)\s*cm\s*高', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # ===== H8: L*W*Hcm外径 =====
    m = re.search(r'([\d.]+)\*([\d.]+)\*([\d.]+)cm\s*外径', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True), '外径')
    
    # ===== P1: 材料n个【Hcm高】;L*Wmm【内径尺寸】 (材料直接+数量,无"-"号) =====
    # 特硬50个【10厘米高】;260*250mm【内径尺寸】
    m = re.search(r'(.+?)(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)mm(?:【.*?)?(?:;|$)', s)
    if m:
        return (mat_map(m.group(1)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(3))], reverse=True), '内径')
    
    # ===== P1b: 材料n个【Hcm高】;L*W(无标记) =====
    m = re.search(r'(.+?)(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)(?:mm|MM)?(?:【.*?)?(?:;|$)', s)
    if m:
        return (mat_map(m.group(1)), sorted([int(m.group(4)), int(m.group(5)), int(m.group(3))], reverse=True), '内径')
    
    # ===== P2: 材料 n个【Hcm高】;L*Wmm =====
    # 超级超级硬 50个【6厘米高];310*300【长宽mm】【内径尺寸】
    # 注意：这里的】可能是] 
    m = re.search(r'(.+?)\s+(\d+)个【(\d+)厘米高[\]】][^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM)?', s)
    if m:
        return (mat_map(m.group(1)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(3))], reverse=True), '内径')
    
    # ===== P2b: 材料 n个【Hcm高】;L*Wmm (无长宽标记) =====
    m = re.search(r'(.+?)\s+(\d+)个【(\d+)厘米高[\]】][^；;]*[；;](\d+)\*(\d+)(?:\*?)mm', s)
    if m:
        return (mat_map(m.group(1)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(3))], reverse=True), '内径')
    
    # ===== P3: 材料-数量【Hcm高】;L*Wmm =====
    m = re.search(r'(.+?)-(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?', s)
    if m:
        return (mat_map(m.group(1)), sorted([round(int(m.group(4))/10,1) if m.group(6) in ('mm','MM') else int(m.group(4)), round(int(m.group(5))/10,1) if m.group(6) in ('mm','MM') else int(m.group(5)), int(m.group(3))], reverse=True), '内径')
    
    # ===== P4: 【Hcm高】材料-数量;L*W =====
    m = re.search(r'【(\d+)厘米高】(.+?)-(\d+)个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?', s)
    if m:
        unit = m.group(6) if m.lastindex >= 6 else ''
        if unit in ('mm','MM'):
            return (mat_map(m.group(2)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(1))], reverse=True), '内径')
        return (mat_map(m.group(2)), sorted([float(m.group(4)), float(m.group(5)), int(m.group(1))], reverse=True), '内径')
    
    # ===== P5: 材料-数量【Hmm高】;L*W【长宽mm】 =====
    m = re.search(r'(.+?)-(\d+)个【(\d+)mm高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽mm】?(?:【.*?)?(?:;|$)', s)
    if m:
        return (mat_map(m.group(1)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), round(int(m.group(3))/10,1)], reverse=True), '内径')
    
    # ===== P6: 材料n个【Hmm高】;L*Wmm =====
    m = re.search(r'(.+?)(\d+)个【(\d+)mm高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*mm?', s)
    if m:
        return (mat_map(m.group(1)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), round(int(m.group(3))/10,1)], reverse=True), '内径')
    
    # ===== HG: n个材料Hmm高;长宽LxWmm =====
    # 50个特硬100mm高;长宽34x33cm
    m = re.search(r'(\d+)个(.+?)(\d+)mm高[^；;]*[；;]长宽([\d.]+)x([\d.]+)\s*(cm|mm)', s)
    if m:
        l = round(float(m.group(4))/10,1) if m.group(6)=='mm' else float(m.group(4))
        w = round(float(m.group(5))/10,1) if m.group(6)=='mm' else float(m.group(5))
        return (mat_map(m.group(2)), sorted([l, w, round(int(m.group(3))/10,1)], reverse=True), '内径')
    
    # ===== HG2: n个材料Hmm高;长宽LxW(无单位) =====
    m = re.search(r'(\d+)个(.+?)(\d+)mm高[^；;]*[；;]长宽([\d.]+)x([\d.]+)', s)
    if m:
        return (mat_map(m.group(2)), sorted([float(m.group(4)), float(m.group(5)), round(int(m.group(3))/10,1)], reverse=True), '内径')
    
    # ===== LN1: 长度Hcm---材料-n个组;W*H【宽高】 =====
    m = re.search(r'长度(\d+)cm---(.+?)-(\d+)个[组\]]*[^；;]*[；;](\d+)\*(\d+)【宽高】', s)
    if m:
        return (mat_map(m.group(2)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(1))], reverse=True), '内径')
    
    # ===== LN2: 长度Hcm--材料-n个组;W*H【宽高】 =====
    m = re.search(r'长度(\d+)cm--(.+?)-(\d+)个[组\]]*[^；;]*[；;](\d+)\*(\d+)【宽高】', s)
    if m:
        return (mat_map(m.group(2)), sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(1))], reverse=True), '内径')
    
    # ===== SP: 长*宽L*W；n个高度Hmm【材料】 =====
    # 长*宽100*100；10个 高度50mm【原色】
    m = re.search(r'长\*宽(\d+)\*(\d+)[^；;]*[；;](\d+)个\s*高度(\d+)mm【(.+?)】', s)
    if m:
        return (mat_map(m.group(5)), sorted([int(m.group(1)), int(m.group(2)), round(int(m.group(4))/10,1)], reverse=True), '外径')
    
    # ===== S1: n个材料*LxWxH (直接前导格式) =====
    m = re.search(r'^(\d+)个(.+?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(2)), sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True), '外径')
    
    # ===== S2: 材料【颜色n个/组】*LxWxH =====
    m = re.search(r'^(.+?)【[^】]+?\d+个[^】]*?】[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(2)), float(m.group(3)), float(m.group(4))], reverse=True), '外径')
    
    # ===== S3: 材料【n个】*LxWxH =====
    m = re.search(r'^(.+?)【(\d+)个】[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True), '外径')
    
    # ===== S4: 材料n个/组*LxWxH =====
    m = re.search(r'^(.+?)(\d+)个[组/]*[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(1)), sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True), '外径')
    
    # ===== S5: 材料内尺寸/外尺寸【n个】*L*W*H =====
    m = re.search(r'(.+?)(?:内尺寸|内径|内寸).+?【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        return (mat_map(m.group(1)), sorted([int(m.group(3)), int(m.group(4)), int(m.group(5))], reverse=True), '内径')
    
    m = re.search(r'(.+?)(?:外尺寸|外径|外寸).+?【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)', s)
    if m:
        return (mat_map(m.group(1)), sorted([int(m.group(3)), int(m.group(4)), int(m.group(5))], reverse=True), '外径')
    
    # ===== S6: 颜色【n个】材料*LxWxH =====
    m = re.search(r'^(.+?)【(\d+)个】(.+?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)', s)
    if m:
        return (mat_map(m.group(1) + m.group(3)), sorted([float(m.group(4)), float(m.group(5)), float(m.group(6))], reverse=True), '外径')
    
    # ===== SP2: 【9长系列】LxWxH；优质【n个】 =====
    m = re.search(r'【9长系列】([\d.]+)x([\d.]+)x([\d.]+)[^；;]*[；;](.+?)【\d+个】', s)
    if m:
        return (mat_map(m.group(4)), sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True), '外径')
    
    # ===== SP3: 长x宽【LxW】高+0.5;材料高度【Hcm】 =====
    m = re.search(r'长x宽【([\d.]+)x([\d.]+)】[^；;]*[；;](.+?)高度【(\d+)厘米】', s)
    if m:
        return (mat_map(m.group(3)), sorted([float(m.group(1)), float(m.group(2)), int(m.group(4))], reverse=True), '外径')
    
    m = re.search(r'长x宽【([\d.]+)x([\d.]+)】[^；;]*[；;]高度【(\d+)厘米】', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True), '外径')
    
    # ===== SP4: 长【L】cm；宽【W】cm；材料 =====
    m = re.search(r'长【(\d+)】cm[^；;]*[；;]宽【(\d+)】cm[^；;]*[；;](.+?)(?:【.*?】)?$', s)
    if m:
        return (mat_map(m.group(3)), sorted([int(m.group(1)), int(m.group(2)), 999], reverse=True), '外径')
    
    # ===== SP5: 特价一组【型号】：L*W*Hcm =====
    m = re.search(r'特价\s+\d+个一组[^；;]*[；;]【[^】]+】[：:]?([\d.]+)\*([\d.]+)\*([\d.]+)cm', s)
    if m:
        return ('特硬', sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True), '外径')
    
    # ===== 兜底: 任何包含材料的直接LxWxH格式 *LxWxH =====
    m = re.search(r'[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)[\*x](\d+(?:\.\d+)?)\s*$', s)
    if m:
        # 尝试从前面提取材料名
        front = s[:m.start()]
        mat = '特硬'
        for kw in ['双面白色','双面白','白色','台湾纸','台湾黄','超硬','特硬','特价','特惠','优质','黄色','白盒','加强','玖龙','牛皮','E坑']:
            if kw in front:
                mat = mat_map(kw)
                break
        return (mat, sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True), '外径')
    
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
    
    if (idx + 1) % 5000 == 0:
        print(f'  {idx+1}/{len(target)}...')

print('\n=== 统计 ===')
for k, v in sorted(stats.items()):
    print(f'  {k}: {v}')
print(f'\n匹配成功: {len(matched_new)}')
print(f'无匹配: {len(nomatch_new)}')

if matched_new:
    batch = 1
    flist = [f for f in os.listdir(OUT_DIR) if f.startswith('\u6362\u7ed1') and f.endswith('.xlsx') and '\u90e8\u5206' not in f]
    if flist:
        nums = [int(re.search(r'\u7b2c(\d+)\u6279', f).group(1)) for f in flist if re.search(r'\u7b2c(\d+)\u6279', f)]
        batch = max(nums) + 1 if nums else 1
    fname = os.path.join(OUT_DIR, f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{batch}\u6279.xlsx')
    pd.DataFrame(matched_new, columns=['店铺名称', '平台商品id', '平台规格id', '商品编码']).to_excel(fname, index=False)
    print(f'✅ 换绑文件_第{batch}批: {len(matched_new)}条')
    if len(matched_new) > 3000:
        import math
        parts = math.ceil(len(matched_new) / 3000)
        for pi in range(parts):
            start = pi * 3000
            end = min((pi + 1) * 3000, len(matched_new))
            pfname = os.path.join(OUT_DIR, f'\u6362\u7ed1\u6587\u4ef6_\u7b2c{batch}\u6279_\u7b2c{pi+1}\u90e8\u5206.xlsx')
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
