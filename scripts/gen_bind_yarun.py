# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市亚润包装材料有限公司'

print('读取中...')
df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(shop_data)} 条')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# ===== 解析器 =====
def p1(s):
    """宽高N*N黄色；长Ncm"""
    m = re.search(r'宽高\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)', s)
    if not m: return None
    w, h = float(m.group(1)), float(m.group(2))
    m = re.search(r'长\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p2(s):
    """宽高N*N黄色内径；长Ncm"""
    return p1(s)

def p3(s):
    """【长宽N*N】；【高Ncm】黄色"""
    m = re.search(r'【长宽\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*】', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【高\s*(\d[\d.]*)\s*cm】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p4(s):
    """长*宽【N*N】；内径Ncm高度-白色"""
    m = re.search(r'长\*宽【\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*】', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'内径\s*(\d[\d.]*)\s*cm\s*高度', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p5(s):
    """长宽【N*N】超硬黄色；内径Ncm高"""
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*】', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'内径\s*(\d[\d.]*)\s*cm\s*高', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p6(s):
    """长*宽【N*N】；外径Ncm白色高"""
    m = re.search(r'长\*宽【\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*】', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'外径\s*(\d[\d.]*)\s*cm\s*白色\s*高', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p7(s):
    """（内径)Ncm高度-特硬;长x宽【NxN】cm"""
    m = re.search(r'[（(]\s*内径\s*[）)]?\s*(\d[\d.]*)\s*cm\s*高度', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[xX×]宽【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p8(s):
    """【长宽N*N】；高Ncm】黄色内径"""
    m = re.search(r'【长宽\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*】', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高\s*(\d[\d.]*)\s*cm】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p9(s):
    """（内径)Nmm高度-特硬;长x宽【NxN】mm【N个】"""
    m = re.search(r'[（(]内径[）)]?\s*(\d[\d.]*)\s*mm\s*高度', s)
    if not m: return None
    h = float(m.group(1))/10
    m = re.search(r'长[xX×]宽【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】mm', s)
    if not m: return None
    l, w = float(m.group(1))/10, float(m.group(2))/10
    return (l, w, h)

def p10(s):
    """【外径】Ncm高度-特硬;长x宽【NxN】cm"""
    m = re.search(r'【\s*外径\s*】\s*(\d[\d.]*)\s*cm\s*高度', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[xX×]宽【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p11_12(s):
    """【高度Ncm】黑色【内/外径】;【长宽N*N】"""
    m = re.search(r'【高度\s*(\d[\d.]*)\s*cm】', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'【长宽\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*】', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p13(s):
    """【长宽N*N】；【高度Ncm】白色外径"""
    m = re.search(r'【长宽\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*】', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【高度\s*(\d[\d.]*)\s*cm】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p14(s):
    """长Ncm；【宽X高】N*Ncm；特硬外尺寸"""
    m = re.search(r'长\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    m = re.search(r'【宽[Xx]高】\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    w, h = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p15(s):
    """【外径】Nmm高度-特硬;长x宽【NxN】mm【N个】"""
    m = re.search(r'【外径】\s*(\d[\d.]*)\s*mm\s*高度', s)
    if not m: return None
    h = float(m.group(1))/10
    m = re.search(r'长[xX×]宽【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】mm', s)
    if not m: return None
    l, w = float(m.group(1))/10, float(m.group(2))/10
    return (l, w, h)

def p17(s):
    """高Ncm黑内；NXN"""
    m = re.search(r'高\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)', s.split('；')[-1] if '；' in s else s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p18(s):
    """高Ncm黑外；NXN"""
    return p17(s)

def p19(s):
    """（黑色)Nmm高度-特硬【N个】;长x宽【NxN】mm"""
    m = re.search(r'[（(]黑色[）)]?\s*(\d[\d.]*)\s*mm\s*高度', s)
    if not m: return None
    h = float(m.group(1))/10
    m = re.search(r'长[xX×]宽【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】mm', s)
    if not m: return None
    l, w = float(m.group(1))/10, float(m.group(2))/10
    return (l, w, h)

def p20(s):
    """（黑色)Nmm高度-特硬【N个】;长x宽【NxN】mm【高+Nmm】"""
    # 解析与p19相同，但内外径不同
    m = re.search(r'[（(]黑色[）)]?\s*(\d[\d.]*)\s*mm\s*高度', s)
    if not m: return None
    h = float(m.group(1))/10
    m = re.search(r'长[xX×]宽【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】mm', s)
    if not m: return None
    l, w = float(m.group(1))/10, float(m.group(2))/10
    return (l, w, h)

def p24(s):
    """【外径】Ncm高度-特硬;长x宽【NxN】mm【N个】"""
    m = re.search(r'【外径】\s*(\d[\d.]*)\s*cm\s*高度', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[xX×]宽【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】mm', s)
    if not m: return None
    l, w = float(m.group(1))/10, float(m.group(2))/10
    return (l, w, h)

def p25_30(s):
    """N×N×Ncm；..."""
    m = re.search(r'(\d[\d.]*)\s*[×*xX]\s*(\d[\d.]*)\s*[×*xX]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    vals = sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True)
    return (vals[0], vals[1], vals[2])

def p31(s):
    """长【N*N】外尺寸；【高Ncm】黄色"""
    m = re.search(r'长【\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*】', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【高\s*(\d[\d.]*)\s*cm】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p32(s):
    """【N*N】黄色；长Ncm"""
    m = re.search(r'【\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*】', s)
    if not m: return None
    w, h0 = float(m.group(1)), float(m.group(2))
    m = re.search(r'长\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h0)

def p33(s):
    """（外径)Ncm高度-特硬;长x宽【NxN】cm"""
    m = re.search(r'[（(]外径[）)]?\s*(\d[\d.]*)\s*cm\s*高度', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[xX×]宽【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

# ===== 结构配置 =====
STRUCT_CONFIG = {
    '宽高N*N黄色；长Ncm;宽高N*N黄色;长Ncm': ('外径', '特硬', p1),
    '宽高N*N黄色内径；长Ncm;宽高N*N黄色内径;长Ncm': ('内径', '特硬', p2),
    '【长宽N*N】；【高Ncm】黄色;【长宽N*N】;【高Ncm】黄色': ('外径', '特硬', p3),
    '长*宽【N*N】；内径Ncm高度-白色;长*宽【N*N】;内径Ncm高度-白色': ('内径', '白色', p4),
    '长宽【N*N】超硬黄色；内径Ncm高;长宽【N*N】超硬黄色;内径Ncm高': ('内径', '超硬', p5),
    '长*宽【N*N】；外径Ncm白色高;长*宽【N*N】;外径Ncm白色高': ('外径', '白色', p6),
    '（内径)Ncm高度-特硬;长x宽【NxN】cm;（内径)Ncm高度-特硬': ('内径', '特硬', p7),
    '【长宽N*N】；高Ncm】黄色内径;【长宽N*N】;高Ncm】黄色内径': ('内径', '特硬', p8),
    '（内径)Nmm高度-特硬;长x宽【NxN】mm【N个】': ('内径', '特硬', p9),
    '【外径】Ncm高度-特硬;长x宽【NxN】cm;【外径】Ncm高度-特硬': ('外径', '特硬', p10),
    '【高度Ncm】黑色【内径】;【长宽N*N】': ('内径', '黑色', p11_12),
    '【高度Ncm】黑色【外径】;【长宽N*N】': ('外径', '黑色', p11_12),
    '【长宽N*N】；【高度Ncm】白色外径;【长宽N*N】;【高度Ncm】白色外径': ('外径', '白色', p13),
    '长Ncm；【宽X高】N*Ncm；特硬外尺寸;长Ncm;【宽X高】N*Ncm;特硬外尺寸': ('外径', '特硬', p14),
    '【外径】Nmm高度-特硬;长x宽【NxN】mm【N个】': ('外径', '特硬', p15),
    '高Ncm红外；N*N;高Ncm红外;N*N': ('定制', None, None),
    '高Ncm黑内；NXN;高Ncm黑内;NXN': ('内径', '黑色', p17),
    '高Ncm黑外；NXN;高Ncm黑外;NXN': ('外径', '黑色', p18),
    '（黑色)Nmm高度-特硬【N个】;长x宽【NxN】mm;（黑色)Nmm高度-特硬【N个】': ('外径', '黑色', p19),
    '（黑色)Nmm高度-特硬【N个】;长x宽【NxN】mm【高+Nmm】;（黑色)Nmm高度-特硬【N个】': ('内径', '黑色', p20),
    '高Ncm红内；N*N;高Ncm红内;N*N': ('定制', None, None),
    '【红色】Nmm高度-特硬【N个】;长x宽【NxN】mm;【红色】Nmm高度-特硬【N个】': ('定制', None, None),
    '【红色】Nmm高度-特硬【N个】;长x宽【NxN】mm【高+Nmm】;【红色】Nmm高度-特硬【N个】': ('定制', None, None),
    '【外径】Ncm高度-特硬;长x宽【NxN】mm【N个】': ('外径', '特硬', p24),
    'N×N×Ncm；双面白色-外尺寸;N×N×Ncm;双面白色-外尺寸': ('外径', '白色', p25_30),
    'N×N×Ncm；特硬黄色-外尺寸;N×N×Ncm;特硬黄色-外尺寸': ('外径', '特硬', p25_30),
    'N×N×Ncm；超硬黄色-外尺寸;N×N×Ncm;超硬黄色-外尺寸': ('外径', '超硬', p25_30),
    'N×N×Ncm；双面白色-外尺寸【N个】;N×N×Ncm;双面白色-外尺寸【N个】': ('外径', '白色', p25_30),
    'N×N×Ncm；特硬黄色-外尺寸【N个】;N×N×Ncm;特硬黄色-外尺寸【N个】': ('外径', '特硬', p25_30),
    'N×N×Ncm；超硬黄色-外尺寸【N个】;N×N×Ncm;超硬黄色-外尺寸【N个】': ('外径', '超硬', p25_30),
    '长【N*N】外尺寸；【高Ncm】黄色;长【N*N】外尺寸;【高Ncm】黄色': ('外径', '特硬', p31),
    '【N*N】黄色；长Ncm;【N*N】黄色;长Ncm': ('外径', '特硬', p32),
    '（外径)Ncm高度-特硬;长x宽【NxN】cm;（外径)Ncm高度-特硬': ('外径', '特硬', p33),
    '高Ncm内红内；N*N;高Ncm内红内;N*N': ('定制', None, None),
    '【红色】Ncm高度-特硬【N个】;长x宽【NxN】mm;【红色】Ncm高度-特硬【N个】': ('定制', None, None),
    '【红色】Ncm高度-特硬【N个】;长x宽【NxN】mm【高+Nmm】;【红色】Ncm高度-特硬【N个】': ('定制', None, None),
}

codes = []
normal_cnt = 0
custom_cnt = 0
noparse_cnt = 0

for idx in range(len(shop_data)):
    row = shop_data.iloc[idx]
    shop = str(row['店铺名称'] or '').strip()
    prod_id = str(row['平台商品id'] or '').strip()
    spec = str(row['平台规格名称'] or '').strip()
    spec_id = str(row['平台规格id'] or '').strip()
    
    sk = make_skeleton(spec)
    cfg = STRUCT_CONFIG.get(sk)
    
    if cfg is None:
        codes.append((shop, prod_id, spec_id, '定制链接'))
        custom_cnt += 1
        continue
    
    dim_kind, material, parser = cfg
    if dim_kind == '定制':
        codes.append((shop, prod_id, spec_id, '定制链接'))
        custom_cnt += 1
        continue
    
    dims = parser(spec)
    if dims is None:
        codes.append((shop, prod_id, spec_id, '定制链接'))
        noparse_cnt += 1
        continue
    
    l, w, h = dims
    l_int = max(1, int(round(l)))
    w_int = max(1, int(round(w)))
    h_int = max(1, int(round(h)))
    km_code = f'{l_int}*{w_int}*{h_int}-{dim_kind}-{material}'
    codes.append((shop, prod_id, spec_id, km_code))
    normal_cnt += 1

print(f'正常编码: {normal_cnt}, 定制链接: {custom_cnt}, 解析失败(当定制): {noparse_cnt}, 合计: {len(codes)}')

outpath = r'D:\Desktop\换绑_深圳市亚润包装材料有限公司.xlsx'
wb = oxl.Workbook()
ws = wb.active
ws.title = 'Sheet1'
ws.append([None, '商品对应表', None, None])
ws.append(['店铺名称', '平台商品id', '平台规格id', '商品编码'])
for row_data in codes:
    ws.append(list(row_data))
ws.column_dimensions['A'].width = 30
ws.column_dimensions['B'].width = 18
ws.column_dimensions['C'].width = 18
ws.column_dimensions['D'].width = 25
wb.save(outpath)
wb.close()
print(f'✅ {outpath}')
