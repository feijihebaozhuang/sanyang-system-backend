# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市三羊包装材料有限公司'

print('读取中...')
df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(shop_data)} 条')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# ===== 解析器 =====
def p_lw_dim(s):
    """长*宽【N*N】cm/【N*N】；外尺寸XXX；【Ncm高】/Ncm高"""
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】\s*(cm)?', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'【?\s*([\d.]+)\s*\.?\s*(\d*)\s*cm\s*高】?', s)
    if not m:
        m = re.search(r'([\d.]+)\s*\.?\s*(\d*)\s*cm\s*高', s)
    if not m: return None
    h = float(m.group(1) + ('.' + m.group(2) if m.group(2) else ''))
    return (l, w, h)

def p_lw_dim_cm(s):
    """长*宽【N*N】cm;外尺寸白色【Ncm高】"""
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'【\s*([\d.]+)\s*cm\s*高】', s)
    if not m:
        m = re.search(r'【\s*([\d.]+)\s*\.?\s*(\d*)\s*cm\s*高】', s)
        if m:
            h = float(m.group(1) + ('.' + m.group(2) if m.group(2) else ''))
        else:
            return None
    else:
        h = float(m.group(1))
    return (l, w, h)

def p8(s):
    """特硬牛皮色【长*宽】N*N;【高】NcmN个一组"""
    m = re.search(r'【长\*宽】\s*([\d.]+)\s*\*\s*([\d.]+)', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'【高】\s*([\d.]+)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p9_10(s):
    """宽高N*N（牛皮色/白色）;长NcmSN级硬度"""
    m = re.search(r'宽高\s*([\d.]+)\s*\*\s*([\d.]+)', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长\s*([\d.]+)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p15_16(s):
    """外尺寸【长*宽】N*N;【高】Ncm红色/黑色"""
    m = re.search(r'外尺寸【长\*宽】\s*([\d.]+)\s*\*\s*([\d.]+)', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'【高】\s*([\d.]+)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p23(s):
    """长*宽【N*N】；外尺寸N级特硬原色；【N高】（无cm的情况）"""
    return p_lw_dim(s)

def p24(s):
    """长*宽【N*N】cm；外尺寸N级特硬原色；【【Ncm高】"""
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'【【\s*([\d.]+)\s*cm\s*高】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p25(s):
    """长*宽【N*N】cm；外尺寸N级特硬原色；【外尺寸】【Ncm高】特硬牛皮色"""
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'【外尺寸】\s*【\s*([\d.]+)\s*cm\s*高】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p26(s):
    """长*宽【N*Ncm；外尺寸N级特硬原色；【Ncm高】（缺]括号）"""
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'【\s*([\d.]+)\s*cm\s*高】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p27(s):
    """长*宽【N*N】c；外尺寸特硬原色；【Ncm高】（缺m）"""
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】c', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'【\s*([\d.]+)\s*cm\s*高】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

STRUCT_CONFIG = {
    '长*宽【N*N】cm；外尺寸N级特硬原色；【Ncm高】;长*宽【N*N】cm;外尺寸N级特硬原色;【Ncm高】': ('外径', '特硬', p_lw_dim),
    '长*宽【N*N】；外尺寸特硬双面白；【Ncm高】;长*宽【N*N】;外尺寸特硬双面白;【Ncm高】': ('外径', '白色', p_lw_dim),
    '长*宽【N*N】；外尺寸特硬原色；【Ncm高】;长*宽【N*N】;外尺寸特硬原色;【Ncm高】': ('内径', '特硬', p_lw_dim),
    '长*宽【N*N】cm;外尺寸白色【Ncm高】': ('内径', '白色', p_lw_dim_cm),
    '长*宽【N*N】；外尺寸N级特硬原色；【Ncm高】;长*宽【N*N】;外尺寸N级特硬原色;【Ncm高】': ('内径', '特硬', p_lw_dim),
    '长*宽【N*N】；外尺寸特硬双面白色；【Ncm高】;长*宽【N*N】;外尺寸特硬双面白色;【Ncm高】': ('外径', '白色', p_lw_dim),
    '长*宽【N*N】cm；外尺寸特硬双面白色；【Ncm高】;长*宽【N*N】cm;外尺寸特硬双面白色;【Ncm高】': ('外径', '白色', p_lw_dim),
    '特硬牛皮色【长*宽】N*N;【高】NcmN个一组': ('外径', '特硬', p8),
    '宽高N*N（牛皮色）;长NcmSN级硬度': ('外径', '特硬', p9_10),
    '宽高N*N（白色）;长NcmSN级硬度': ('外径', '白色', p9_10),
    '长*宽【N*N】；外尺寸N级特硬双面白；Ncm高;长*宽【N*N】;外尺寸N级特硬双面白;Ncm高': ('外径', '白色', p_lw_dim),
    '长*宽【N*N】；内寸N级特硬双面白；Ncm高;长*宽【N*N】;内寸N级特硬双面白;Ncm高': ('内径', '白色', p_lw_dim),
    '长*宽【N*N】；内寸N级特硬原色；Ncm高;长*宽【N*N】;内寸N级特硬原色;Ncm高': ('内径', '特硬', p_lw_dim),
    '长*宽【N*N】；外尺寸N级特硬原色；Ncm高;长*宽【N*N】;外尺寸N级特硬原色;Ncm高': ('外径', '特硬', p_lw_dim),
    '外尺寸【长*宽】N*N;【高】Ncm红色': ('定制', None, None),
    '外尺寸【长*宽】N*N;【高】Ncm黑色': ('外径', '黑色', p15_16),
    '长*宽【N*N】；外尺寸N级特硬双面白；【Ncm高】;长*宽【N*N】;外尺寸N级特硬双面白;【Ncm高】': ('外径', '白色', p_lw_dim),
    '长*宽【N*N】；外尺寸N级超硬原色；【Ncm高】;长*宽【N*N】;外尺寸N级超硬原色;【Ncm高】': ('外径', '超硬', p_lw_dim),
    '长*宽【N*N】；内寸N级特硬原色；【Ncm高】;长*宽【N*N】;内寸N级特硬原色;【Ncm高】': ('内径', '特硬', p_lw_dim),
    '长*宽【N*N】；内寸N级超硬原色；【Ncm高】;长*宽【N*N】;内寸N级超硬原色;【Ncm高】': ('内径', '超硬', p_lw_dim),
    '长*宽【N*N】cm；外尺寸【双面红】；【Ncm高】;长*宽【N*N】cm;外尺寸【双面红】;【Ncm高】': ('定制', None, None),
    '长*宽【N*N】cm；外尺寸【双面黑】；【Ncm高】;长*宽【N*N】cm;外尺寸【双面黑】;【Ncm高】': ('外径', '黑色', p_lw_dim),
    '长*宽【N*N】；外尺寸N级特硬原色；【N高】;长*宽【N*N】;外尺寸N级特硬原色;【N高】': ('内径', '特硬', p_lw_dim),
    '长*宽【N*N】cm；外尺寸N级特硬原色；【【Ncm高】;长*宽【N*N】cm;外尺寸N级特硬原色;【【Ncm高】': ('外径', '特硬', p24),
    '长*宽【N*N】cm；外尺寸N级特硬原色；【外尺寸】【Ncm高】特硬牛皮色;长*宽【N*N】cm;外尺寸N级特硬原色;【外尺寸】【Ncm高】特硬牛皮色': ('外径', '特硬', p25),
    '长*宽【N*Ncm；外尺寸N级特硬原色；【Ncm高】;长*宽【N*Ncm;外尺寸N级特硬原色;【Ncm高】': ('外径', '特硬', p26),
    '长*宽【N*N】c；外尺寸特硬原色；【Ncm高】;长*宽【N*N】c;外尺寸特硬原色;【Ncm高】': ('内径', '特硬', p27),
    '特硬;飞机盒': ('定制', None, None),
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

outpath = r'D:\Desktop\换绑_深圳市三羊包装材料有限公司.xlsx'
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
