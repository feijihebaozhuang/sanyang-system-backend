# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市正方形纸制品有限公司'

print('读取中...')
df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(shop_data)} 条')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# ===== 各骨架解析器 =====
def parse1(s):
    """长宽NxNcm；Ncm外径"""
    m = re.search(r'长[宽度]*([\d.]+)\s*[xX×]\s*([\d.]+)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'(\d[\d.]*)\s*cm\s*外径', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def parse2(s):
    """长宽NxNcm；Ncm内径"""
    m = re.search(r'长[宽度]*([\d.]+)\s*[xX×]\s*([\d.]+)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'(\d[\d.]*)\s*cm\s*内径', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def parse3(s):
    """NxN；Ncm白色"""
    m = re.search(r'([\d.]+)\s*[xX×]\s*([\d.]+)[^N]*?(\d[\d.]*)\s*cm\s*白色', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    h = float(m.group(3))
    return (l, w, h)

def parse4(s):
    """NxN；Ncm黑色"""
    m = re.search(r'([\d.]+)\s*[xX×]\s*([\d.]+)[^N]*?(\d[\d.]*)\s*cm\s*黑色', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    h = float(m.group(3))
    return (l, w, h)

def parse5(s):
    """长宽NxN；高Ncm内径白色"""
    m = re.search(r'长[宽度]*([\d.]+)\s*[xX×]\s*([\d.]+)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高\s*(\d[\d.]*)\s*cm\s*内径', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def parse6(s):
    """长宽NxN；高Ncm外径白色"""
    m = re.search(r'长[宽度]*([\d.]+)\s*[xX×]\s*([\d.]+)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高\s*(\d[\d.]*)\s*cm\s*外径', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def parse7(s):
    """高度Ncm白色*NXN"""
    m = re.search(r'高度\s*(\d[\d.]*)\s*cm\s*白色\s*\*\s*([\d.]+)\s*[xX×]\s*([\d.]+)', s)
    if not m: return None
    h = float(m.group(1))
    l = float(m.group(2))
    w = float(m.group(3))
    return (l, w, h)

def parse8(s):
    """高度Ncm红色*NXN → 定制链接"""
    return None

def parse9(s):
    """高度Ncm蓝色*NXN → 定制链接"""
    return None

def parse10(s):
    """高度Ncm黑色*NXN"""
    m = re.search(r'高度\s*(\d[\d.]*)\s*cm\s*黑色\s*\*\s*([\d.]+)\s*[xX×]\s*([\d.]+)', s)
    if not m: return None
    h = float(m.group(1))
    l = float(m.group(2))
    w = float(m.group(3))
    return (l, w, h)

def parse11(s):
    """高度Ncm内径*长宽N*Ncm优质黄色"""
    m = re.search(r'高度\s*(\d[\d.]*)\s*cm\s*内径', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*([\d.]+)\s*[xX×]\s*([\d.]+)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def parse12(s):
    """高度Ncm外径*长宽N*Ncm优质黄色"""
    m = re.search(r'高度\s*(\d[\d.]*)\s*cm\s*外径', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*([\d.]+)\s*[xX×]\s*([\d.]+)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def parse13(s):
    """E瓦;特硬 → 定制链接"""
    return None

STRUCT_CONFIG = {
    '长宽NxNcm；Ncm外径;长宽NxNcm;Ncm外径': ('外径', '特硬', parse1),
    '长宽NxNcm；Ncm内径;长宽NxNcm;Ncm内径': ('内径', '特硬', parse2),
    'NxN；Ncm白色;NxN;Ncm白色': ('外径', '白色', parse3),
    'NxN；Ncm黑色;NxN;Ncm黑色': ('外径', '黑色', parse4),
    '长宽NxN；高Ncm内径白色;长宽NxN;高Ncm内径白色': ('内径', '白色', parse5),
    '长宽NxN；高Ncm外径白色;长宽NxN;高Ncm外径白色': ('外径', '白色', parse6),
    '高度Ncm白色*NXN;NXN;高度Ncm白色': ('外径', '白色', parse7),
    '高度Ncm红色*NXN;NXN;高度Ncm红色': ('定制', None, parse8),
    '高度Ncm蓝色*NXN;NXN;高度Ncm蓝色': ('定制', None, parse9),
    '高度Ncm黑色*NXN;NXN;高度Ncm黑色': ('外径', '黑色', parse10),
    '高度Ncm内径*长宽N*Ncm优质黄色;长宽N*Ncm优质黄色;高度Ncm内径': ('内径', '特硬', parse11),
    '高度Ncm外径*长宽N*Ncm优质黄色;长宽N*Ncm优质黄色;高度Ncm外径': ('外径', '特硬', parse12),
    'E瓦;特硬': ('定制', None, parse13),
}

codes = []
normal_cnt = 0
custom_cnt = 0

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
        custom_cnt += 1
        continue
    
    l, w, h = dims
    l_int = int(round(l))
    w_int = int(round(w))
    h_int = int(round(h))
    km_code = f'{l_int}*{w_int}*{h_int}-{dim_kind}-{material}'
    codes.append((shop, prod_id, spec_id, km_code))
    normal_cnt += 1

print(f'正常编码: {normal_cnt}, 定制链接: {custom_cnt}, 合计: {len(codes)}')

outpath = r'D:\Desktop\换绑_深圳市正方形纸制品有限公司.xlsx'
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
