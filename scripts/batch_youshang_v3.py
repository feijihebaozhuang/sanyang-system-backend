# -*- coding: utf-8 -*-
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
    # 白色系
    if '双面白色' in m or '双面白' in m or '特硬双面白' in m: return '白色'
    if '白盒' in m: return '白色'
    if m == '白色' or m == '白色纸': return '白色'
    # 超硬系
    if '超硬台湾' in m or '台湾纸超硬' in m or '台湾黄超硬' in m: return '超硬'
    if '台湾纸' in m or '台湾黄' in m: return '超硬'
    if '超硬' in m: return '超硬'
    if '超级' in m: return '超硬'  # 超级超级硬→超硬
    # 特硬系
    if '特惠' in m: return '特硬'
    if '特硬' in m or '特价' in m: return '特硬'
    if '黄色' in m: return '特硬'
    if '牛皮色' in m or '牛皮' in m: return '特硬'
    if '原色' in m: return '特硬'
    if '玖龙' in m or 'S级' in m: return '特硬'
    if 'E坑' in m: return '特硬'
    if '加强' in m: return '特硬'
    if '高档' in m: return '特硬'
    # 优质
    if '优质' in m: return '优质'
    # 白色兜底
    if '白色' in m or '白' in m: return '白色'
    if '红色' in m: return '特硬'
    return m.strip()

def spec_clean(s):
    """清理规格名称中的脏数据"""
    # 去掉重复段
    parts = s.split(';')
    seen = set()
    clean = []
    for p in parts:
        p = p.strip()
        if p and p not in seen:
            seen.add(p)
            clean.append(p)
    return ';'.join(clean)

# 预编译所有正则（按优先级从高到低）
PATTERNS = []

# ===== P1: 数量前导直接格式 =====
# 100个材料*LxWxH;... 或 材料100个*LxWxH
# 例: 100个双面白色*10*10*6.5 / 特硬【白色100个】*19.1x12.5x9.7
PATTERNS.append((
    r'^(?:(\d+)个)?(.+?)(?:\d+个)?[\*x]([\d.]+)[\*x]([\d.]+)[\*x]([\d.]+)',
    lambda m: (
        mat_map(m.group(2)),
        sorted([float(m.group(3)), float(m.group(4)), float(m.group(5))], reverse=True),
        '外径'
    )
))

# ===== P2: 【2厘米高】材料-数量;L*W【长宽】CM【内径尺寸】 =====
# 例: 【2厘米高】双面白-100个;10*6【长宽】CM【内径尺寸】
PATTERNS.append((
    r'【(\d+)厘米高】(.+?)-(\d+)个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】\s*(?:CM|cm|MM|mm)(?:【内径.*?)?(?:;|$)',
    lambda m: (
        mat_map(m.group(2)),
        sorted([float(m.group(4)), float(m.group(5)), int(m.group(1))], reverse=True),
        '内径'
    )
))

# ===== P3: 材料-数量【H厘米高】;L*W【长宽】MM【内径尺寸】 =====
# 例: 特硬黄-100个【10厘米高】;140*140【长宽】MM
# 含变体 材料-数量【H厘米高】;L*W*【长宽】MM【内径尺寸】
PATTERNS.append((
    r'(.+?)-(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】\s*(?:CM|cm|MM|mm)(?:【.*?)?(?:;|$)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([float(m.group(4)), float(m.group(5)), int(m.group(3))], reverse=True),
        '内径'
    )
))

# ===== P4: 材料-数量【Hmm高】;L*W【长宽mm】【内径尺寸】 =====
# 例: 特硬-50个【100mm高】;230*220【长宽mm】
PATTERNS.append((
    r'(.+?)-(\d+)个【(\d+)mm高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽mm】(?:【.*?)?(?:;|$)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), round(int(m.group(3))/10,1)], reverse=True),
        '内径'
    )
))

# ===== P5: 50个材料Hmm高;长宽LxWcm/mm【内径尺寸】 =====
# 例: 50个特硬100mm高;长宽34x33cm【内径尺寸】
# 例: 50个特硬100mm高;长宽47x37mm【内径尺寸】
PATTERNS.append((
    r'(\d+)个(.+?)(\d+)mm高[^；;]*[；;]长宽([\d.]+)x([\d.]+)\s*(cm|mm)(?:【.*?)?(?:;|$)',
    lambda m: (
        mat_map(m.group(2)),
        sorted([
            float(m.group(4)) if m.group(6)=='cm' else round(float(m.group(4))/10,1),
            float(m.group(5)) if m.group(6)=='cm' else round(float(m.group(5))/10,1),
            round(int(m.group(3))/10,1)
        ], reverse=True),
        '内径'
    )
))

# ===== P6: 材料-数量【H厘米高】;L*W【长宽】CM（无内径标记） =====
# 例: 双面白-100个【2厘米高】;10*8【长宽】CM
# 注意单位是cm
PATTERNS.append((
    r'(.+?)-(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】\s*(?:CM|cm)(?:【.*?)?(?:;|$)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([float(m.group(4)), float(m.group(5)), int(m.group(3))], reverse=True),
        '内径'
    )
))

# ===== P7: 材料-数量【H厘米高】;L*W【长宽】MM（MM单位不同于CM） =====
# 例: 双面白色-100个【10厘米高】;120*120【长宽】MM
# MM→cm要除以10
PATTERNS.append((
    r'(.+?)-(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】\s*(?:MM|mm)(?:【.*?)?(?:;|$)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(3))], reverse=True),
        '内径'
    )
))

# ===== P8: 材料-数量【H厘米高】;L*W【长宽】无单位但有【内径】标记 =====
# 例: 双面白色-100个【2厘米高】;28*8【长宽】 【内径】
PATTERNS.append((
    r'(.+?)-(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】[^；;]*【内径】(?:;|$)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([float(m.group(4)), float(m.group(5)), int(m.group(3))], reverse=True),
        '内径'
    )
))

# ===== P9: 单位mm的【长宽mm】无内径尺寸标记 =====
# 例: 特硬-50个【100mm高】;230*220【长宽mm】
PATTERNS.append((
    r'(.+?)-(\d+)个【(\d+)mm高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽mm】(?:;|$)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), round(int(m.group(3))/10,1)], reverse=True),
        '内径'
    )
))

# ===== P10: 材料-数量【H毫米高】;L*W*【长宽】mm（有星号在长宽前） =====
# 例: 台湾纸-100个【10厘米高】;410*180*【长宽】mm
PATTERNS.append((
    r'(.+?)-(\d+)个【(\d+)(?:mm|厘米)高】[^；;]*[；;](\d+)\*(\d+)\*【长宽】\s*(?:CM|cm|MM|mm)(?:【.*?)?(?:;|$)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([float(m.group(4)), float(m.group(5)), 
                int(m.group(3)) if '厘米' in m.group(0) else round(int(m.group(3))/10,1)], reverse=True),
        '内径'
    )
))

# ===== P11: 材料50个【H厘米高】;L*Wmm（无长宽标记） =====
# 例: 特硬50个【10厘米高】;210*210【长宽mm】
# 例: 白色 50个【10厘米高】;240*230【长宽】mm
PATTERNS.append((
    r'(.+?)(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?(?:【.*?)?(?:;|$)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([float(m.group(4)), float(m.group(5)), int(m.group(3))], reverse=True),
        '内径'
    )
))

# ===== P12: 材料【内径】【数量】*或x L*W*H =====
# 例: 特惠【内径】【100个】*220*220*100
# 例: 内寸【即产品尺寸】特硬台湾纸【100个】*140x140x100
PATTERNS.append((
    r'.+?【内径】.+?【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)',
    lambda m: (
        '特硬',
        sorted([int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))][1:], reverse=True),
        '内径'
    )
))

# 另一种内寸格式
PATTERNS.append((
    r'内寸.+?【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)',
    lambda m: (
        '特硬',
        sorted([int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))][1:], reverse=True),
        '内径'
    )
))

# ===== P13: 材料-内尺寸【数量】*L*W*H =====
# 例: 特惠-内径【100个】*260*260*100
PATTERNS.append((
    r'(.+?)(?:-内尺寸|内尺寸|内径)【?[^【]*?【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))][1:], reverse=True),
        '内径'
    )
))

# ===== P14: 材料【外径】【数量】*L*W*H 或 材料-外尺寸【数量】*L*W*H =====
PATTERNS.append((
    r'(.+?)(?:-外尺寸|外尺寸|外径|外寸)【?[^【]*?【(\d+)个】[\*x](\d+)[\*x](\d+)[\*x](\d+)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))][1:], reverse=True),
        '外径'
    )
))

# ===== P15: 外尺寸【长宽】LxWcm；3层【纸箱】【高】Hcm =====
PATTERNS.append((
    r'外尺寸 【长宽】([\d.]+)x([\d.]+)cm[^；;]*[；;].*?【高】(\d+)cm',
    lambda m: (
        '特硬',
        sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True),
        '外径'
    )
))

# ===== P16: 【内径尺寸】的直接格式 L*W【长宽mm】CM =====
# 例: 特硬-100个【2厘米高】;10*8【长宽】CM【内径尺寸】
# （已包含在P2/P3中）

# ===== P17: 50个材料【H厘米高】;L*Wmm【内径尺寸】（空格分隔） =====
# 例: 白色 50个【10厘米高】;240*230【长宽】mm【内径尺寸】
# 例: 超级超级硬 50个【10厘米高】;310*300【长宽mm】【内径尺寸】
PATTERNS.append((
    r'(.+?)\s+(\d+)个【(\d+)厘米高】[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?(?:【.*?)?(?:;|$)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([float(m.group(4)), float(m.group(5)), int(m.group(3))], reverse=True),
        '内径'
    )
))

# ===== P18: 特价 100个一组；【型号】：L*W*Hcm =====
# 例: 特价 100个一组；【A12】：17.8*15*8.5cm
PATTERNS.append((
    r'特价 \d+个一组[^；;]*[；;]【[^】]+】[：:]?([\d.]+)\*([\d.]+)\*([\d.]+)cm',
    lambda m: (
        '特硬',
        sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True),
        '外径'
    )
))

# ===== P19: L*W*Hcm外径层纸箱 =====
# 例: 12*12*10.5cm外径五层纸箱；五层纸箱；黄色
PATTERNS.append((
    r'([\d.]+)\*([\d.]+)\*([\d.]+)cm\s*外径',
    lambda m: (
        '特硬',
        sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True),
        '外径'
    )
))

# ===== P20: 长度Hcm---材料-数量组;W*H【宽高】MM =====
# 例: 长度11cm---特硬黄-50个组;110*110【宽高】MM
PATTERNS.append((
    r'长度(\d+)cm---(.+?)-(\d+)个[组\]]*[^；;]*[；;](\d+)\*(\d+)【宽高】',
    lambda m: (
        mat_map(m.group(2)),
        sorted([round(int(m.group(4))/10,1), round(int(m.group(5))/10,1), int(m.group(1))], reverse=True),
        '内径'
    )
))

# ===== P21: 高Hcm【层】；长宽【L*W】= 纸箱 =====
PATTERNS.append((
    r'高(\d+)cm【\d+层】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)】',
    lambda m: (
        '特硬',
        sorted([float(m.group(2)), float(m.group(3)), int(m.group(1))], reverse=True),
        '外径'
    )
))

# ===== P22: 高【Hcm】【层纸箱】；长宽【L*Wcm】= 纸箱 =====
PATTERNS.append((
    r'高【(\d+)cm】【[三层五层]+纸箱】[^；;]*[；;]长宽【([\d.]+)\*([\d.]+)cm】',
    lambda m: (
        '特硬',
        sorted([float(m.group(2)), float(m.group(3)), int(m.group(1))], reverse=True),
        '外径'
    )
))

# ===== P23: 高度Hcm【层纸箱】数量;L*W【长宽mm/MM/cm】= 纸箱内径 =====
PATTERNS.append((
    r'高度(\d+)cm【.+?纸箱】\s*\d+个[^；;]*[；;](\d+)\*(\d+)(?:\*?)【长宽】?\s*(?:mm|MM|cm|CM)?(?:【.*?)?(?:;|$)',
    lambda m: (
        '特硬',
        sorted([float(m.group(2)), float(m.group(3)), int(m.group(1))], reverse=True),
        '内径'
    )
))

# ===== P24: 高度Hcm【层纸箱】数量;长宽LxWcm =====
PATTERNS.append((
    r'高度(\d+)cm【.+?纸箱】\s*\d+个[^；;]*[；;]长宽([\d.]+)x([\d.]+)\s*cm',
    lambda m: (
        '特硬',
        sorted([float(m.group(2)), float(m.group(3)), int(m.group(1))], reverse=True),
        '内径'
    )
))

# ===== P25: LxW cm【长宽】;高度Hcm【层纸箱】数量 =====
PATTERNS.append((
    r'([\d.]+)x\s*([\d.]+)\s*cm【长宽】[^；;]*[；;]高度(\d+)cm【.+?纸箱】',
    lambda m: (
        '特硬',
        sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True),
        '外径'
    )
))

# ===== P26: 大规格外径 L*W*H；材料【数量】（优质类） =====
# 例: 7.5*6.5*2.7；优质【100个】
PATTERNS.append((
    r'^([\d.]+)\*([\d.]+)\*([\d.]+)[^；;]*[；;](.+?)【\d+个】',
    lambda m: (
        mat_map(m.group(4)),
        sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True),
        '外径'
    )
))

# ===== P27: 外径【长宽】LxW;高度Hcm【层 纸箱】= 纸箱 =====
PATTERNS.append((
    r'外径【长宽】([\d.]+)x([\d.]+)[^；;]*[；;]高度(\d+)cm【\d+层\s*纸箱】',
    lambda m: (
        '特硬',
        sorted([float(m.group(1)), float(m.group(2)), int(m.group(3))], reverse=True),
        '外径'
    )
))

# ===== P28: A型号【L*W*H】；层材料 数量；材料 =====
# 例: A11【18X13X6.5CM】；三层E硬 50个；牛皮色 特价
PATTERNS.append((
    r'[A-Z]\d+【([\d.]+)[Xx]([\d.]+)[Xx]([\d.]+)CM】',
    lambda m: (
        '特硬',
        sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True),
        '外径'
    )
))

# ===== P29: 材料【数量/组】*LxWxH =====
# 例: 特硬【白色100个/组】*19.1x12.5x9.7
PATTERNS.append((
    r'^(.+?)【.+?】[\*x]([\d.]+)[\*x]([\d.]+)[\*x]([\d.]+)',
    lambda m: (
        mat_map(m.group(1)),
        sorted([float(m.group(2)), float(m.group(3)), float(m.group(4))], reverse=True),
        '外径'
    )
))


def parse_spec(s):
    """解析规格名称，返回 (mat, dims_sorted, dk) 或 None"""
    s = s.strip()
    # 清理明显干扰
    if '24cm高度以上' in s: return ('特硬', (None, None, None), '外径')
    if '加工定制' in s: return None
    if '长【' in s and '宽【' in s: return None  # 格式太特殊
    
    for pat, func in PATTERNS:
        m = re.search(pat, s)
        if m:
            try:
                mat, dims, dk = func(m)
                return (mat, dims, dk)
            except: continue
    return None


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
    
    result = parse_spec(spec_name)
    
    if result and result[1][0] is not None:
        mat, dims, dk = result
        if mat == '特硬':
            pass
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
        print(f'  {idx+1}/{len(target)}...匹配{stats.get("匹配",0)} 无匹配{stats.get("无匹配",0)} 未识别{stats.get("未识别",0)}')

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
