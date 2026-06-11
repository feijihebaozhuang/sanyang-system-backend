# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '飞机盒彩色专卖店'

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
    """宽度：Ncm---高度：Ncm;白色N个长度：Ncm"""
    m = re.search(r'宽度[：:]\s*(\d[\d.]*)\s*cm---高度[：:]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度[：:]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p2(s):
    """白色【N个】宽度NCM;长N*宽?*高N【所量即所装=内径】"""
    m = re.search(r'宽度\s*(\d[\d.]*)\s*CM', s)
    if not m: return None
    w = float(m.group(1))
    parts = s.split(';')
    if len(parts) < 2: return None
    m = re.search(r'长\s*(\d[\d.]*)\s*\*', parts[1])
    if not m: return None
    l = float(m.group(1))
    m = re.search(r'高\s*(\d[\d.]*)', parts[1])
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p3(s):
    """宽度NCM特硬-牛皮色【N个】;长N*宽?*高N【所量即所装=内径】"""
    m = re.search(r'宽度\s*(\d[\d.]*)\s*CM', s)
    if not m: return None
    w = float(m.group(1))
    parts = s.split(';')
    if len(parts) < 2: return None
    m = re.search(r'长\s*(\d[\d.]*)\s*\*', parts[1])
    if not m: return None
    l = float(m.group(1))
    m = re.search(r'高\s*(\d[\d.]*)', parts[1])
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p4(s):
    """宽度---Nmm【高N厘米】;长度---Nmm【数量N个】"""
    m = re.search(r'宽度---(\d[\d.]*)\s*mm', s)
    if not m: return None
    w = float(m.group(1))/10
    m = re.search(r'高(\d[\d.]*)\s*厘米', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长度---(\d[\d.]*)\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10
    return (l, w, h)

def p5(s):
    """【宽度N厘米】【高N厘米】;长度---Nmm【数量N个】"""
    m = re.search(r'宽度\s*(\d[\d.]*)\s*厘米', s)
    if not m: return None
    w = float(m.group(1))
    m = re.search(r'高\s*(\d[\d.]*)\s*厘米', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长度---(\d[\d.]*)\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10
    return (l, w, h)

def p6(s):
    """宽NCM特硬-牛皮色【N个】;长N*宽?*高N【所量即所装=内径】"""
    m = re.search(r'宽\s*(\d[\d.]*)\s*CM', s)
    if not m: return None
    w = float(m.group(1))
    parts = s.split(';')
    if len(parts) < 2: return None
    m = re.search(r'长\s*(\d[\d.]*)\s*\*', parts[1])
    if not m: return None
    l = float(m.group(1))
    m = re.search(r'高\s*(\d[\d.]*)', parts[1])
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p7(s):
    """宽度---Nmm【高N厘米】;【数量N个】【长度N厘米】"""
    m = re.search(r'宽度---(\d[\d.]*)\s*mm', s)
    if not m: return None
    w = float(m.group(1))/10
    m = re.search(r'高(\d[\d.]*)\s*厘米', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'【数量\s*\d+\s*个】\s*【长度\s*(\d[\d.]*)\s*厘米】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p8(s):
    """宽度：Ncm---高度：Ncmm;白色N个长度：Ncm"""
    m = re.search(r'宽度[：:]\s*(\d[\d.]*)\s*cm---高度[：:]\s*(\d[\d.]*)\s*cmm', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度[：:]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p9(s):
    """外尺寸【双面白色】N个;长N宽N高N(cm)"""
    m = re.search(r'长\s*(\d[\d.]*)\s*宽\s*(\d[\d.]*)\s*高\s*(\d[\d.]*)\s*\(cm\)', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2)); h = float(m.group(3))
    return (l, w, h)

def p10(s):
    """进口牛皮色【内尺寸】;长N宽N高N(cm)"""
    return p9(s)

def p11(s):
    """进口牛皮色【外尺寸】;长N宽N高N(cm)"""
    return p9(s)

# ===== 结构配置 =====
STRUCT_CONFIG = {
    '宽度：Ncm---高度：Ncm;白色N个长度：Ncm': ('外径', '白色', p1),
    '白色【N个】宽度NCM;长N*宽?*高N【所量即所装=内径】': ('内径', '白色', p2),
    '宽度NCM特硬-牛皮色【N个】;长N*宽?*高N【所量即所装=内径】': ('内径', '特硬', p3),
    '宽度---Nmm【高N厘米】;长度---Nmm【数量N个】': ('外径', '特硬', p4),
    '【宽度N厘米】【高N厘米】;长度---Nmm【数量N个】': ('外径', '特硬', p5),
    '宽NCM特硬-牛皮色【N个】;长N*宽?*高N【所量即所装=内径】': ('内径', '特硬', p6),
    '宽度---Nmm【高N厘米】;【数量N个】【长度N厘米】': ('外径', '特硬', p7),
    '宽度：Ncm---高度：Ncmm;白色N个长度：Ncm': ('外径', '白色', p8),
    '外尺寸【双面白色】N个;长N宽N高N(cm)': ('外径', '白色', p9),
    '进口牛皮色【内尺寸】;长N宽N高N(cm)': ('内径', '特硬', p10),
    '进口牛皮色【外尺寸】;长N宽N高N(cm)': ('外径', '特硬', p11),
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

outpath = r'D:\Desktop\换绑_飞机盒彩色专卖店.xlsx'
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
