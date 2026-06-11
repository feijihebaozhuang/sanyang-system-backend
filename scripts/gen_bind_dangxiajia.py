# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '当下家包装'

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
    """宽N[N个]内径;长Nmm;高Nmm【浙江发货】"""
    m = re.search(r'宽\s*(\d[\d.]*)\s*\[', s)
    if not m: return None
    w = float(m.group(1))/10
    m = re.search(r'长\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10
    m = re.search(r'高\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p2(s):
    """宽N[N个];长Nmm;高Nmm【浙江发货】"""
    m = re.search(r'宽\s*(\d[\d.]*)\s*\[', s)
    if not m: return None
    w = float(m.group(1))/10
    m = re.search(r'长\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10
    m = re.search(r'高\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p3(s):
    """宽N[N个]【广东发货】;长Nmm;高Nmm"""
    m = re.search(r'宽\s*(\d[\d.]*)\s*\[', s)
    if not m: return None
    w = float(m.group(1))/10
    m = re.search(r'长\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10
    m = re.search(r'高\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p4_7(s):
    """宽N[N个];长Nmm;高Nmm【颜色】"""
    m = re.search(r'宽\s*(\d[\d.]*)\s*\[', s)
    if not m: return None
    w = float(m.group(1))/10
    m = re.search(r'长\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10
    m = re.search(r'高\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p8(s):
    """Ncm内高【白色】N个;N*N【长宽内径】"""
    m = re.search(r'(\d[\d.]*)\s*cm\s*内高', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*【长宽内径】', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p9(s):
    """Nmm高（N个）;NxNmm长宽;特硬飞机盒--白色"""
    m = re.search(r'(\d[\d.]*)\s*mm\s*高', s)
    if not m: return None
    h = float(m.group(1))/10
    m = re.search(r'(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*mm\s*长宽', s)
    if not m: return None
    l, w = float(m.group(1))/10, float(m.group(2))/10
    return (l, w, h)

def p10_13(s):
    """宽N[N个]内尺寸;长Nmm;高Nmm【颜色】"""
    m = re.search(r'宽\s*(\d[\d.]*)\s*\[', s)
    if not m: return None
    w = float(m.group(1))/10
    m = re.search(r'长\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10
    m = re.search(r'高\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p14(s):
    """Nmm（内高）（N个）;NxNmm长宽;特硬飞机盒--白色"""
    m = re.search(r'(\d[\d.]*)\s*mm\s*（内高）', s)
    if not m: return None
    h = float(m.group(1))/10
    m = re.search(r'(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*mm\s*长宽', s)
    if not m: return None
    l, w = float(m.group(1))/10, float(m.group(2))/10
    return (l, w, h)

# ===== 结构配置 =====
STRUCT_CONFIG = {
    '宽N[N个]内径;长Nmm;高Nmm【浙江发货】': ('内径', '特硬', p1),
    '宽N[N个];长Nmm;高Nmm【浙江发货】': ('外径', '特硬', p2),
    '宽N[N个]【广东发货】;长Nmm;高Nmm': ('外径', '特硬', p3),
    '宽N[N个];长Nmm;高Nmm【牛皮色】': ('外径', '特硬', p4_7),
    '宽N[N个];长Nmm;高Nmm【白色】': ('外径', '白色', p4_7),
    '宽N[N个];长Nmm;高Nmm【红色】': ('定制', None, None),
    '宽N[N个];长Nmm;高Nmm【黑色】': ('外径', '黑色', p4_7),
    'Ncm内高【白色】N个;N*N【长宽内径】': ('内径', '白色', p8),
    'Nmm高（N个）;NxNmm长宽;特硬飞机盒--白色': ('外径', '白色', p9),
    '宽N[N个]内尺寸;长Nmm;高Nmm【牛皮色】': ('内径', '特硬', p10_13),
    '宽N[N个]内尺寸;长Nmm;高Nmm【白色】': ('内径', '白色', p10_13),
    '宽N[N个]内尺寸;长Nmm;高Nmm【红色】': ('定制', None, None),
    '宽N[N个]内尺寸;长Nmm;高Nmm【黑色】': ('内径', '黑色', p10_13),
    'Nmm（内高）（N个）;NxNmm长宽;特硬飞机盒--白色': ('内径', '白色', p14),
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

outpath = r'D:\Desktop\换绑_当下家包装.xlsx'
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
