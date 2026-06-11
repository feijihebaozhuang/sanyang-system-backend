# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '东莞市新鑫星包装材料有限公司'

print('读取中...')
df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']

shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(shop_data)} 条')

# ===== 各骨架专用解析 =====
def parse_struct1(s):
    """长宽【NxN】cm；高度【Ncm特硬黄】"""
    m = re.search(r'长[宽度]*[【\[]\s*([\d.]+)\s*[×*xX]\s*([\d.]+)\s*[】\]]', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高[度]*[【\[]\s*([\d.]+)', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def parse_struct2(s):
    """外径白色高【N厘米】；长x宽【NxN】"""
    m = re.search(r'高[【\[]\s*([\d.]+)', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[xX×]宽[【\[]\s*([\d.]+)\s*[xX×]\s*([\d.]+)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def parse_struct4(s):
    """NCM；宽Ncm；高Ncm"""
    m = re.match(r'([\d.]+)\s*CM[；;]\s*宽\s*([\d.]+)\s*cm[；;]\s*高\s*([\d.]+)\s*cm', s, re.I)
    if not m: return None
    return (float(m.group(1)), float(m.group(2)), float(m.group(3)))

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

STRUCT_CONFIG = {
    '长宽【NxN】cm；高度【Ncm特硬黄】;长宽【NxN】cm;高度【Ncm特硬黄】': ('外径', '特硬', parse_struct1),
    '外径白色高【N厘米】；长x宽【NxN】;外径白色高【N厘米】;长x宽【NxN】': ('外径', '白色', parse_struct2),
    '长NCM': None,  # 定制链接
    'NCM；宽Ncm；高Ncm;NCM;宽Ncm;高Ncm': ('外径', '特硬', parse_struct4),
    'NCM': None,  # 定制链接
    'E瓦;特硬': None,  # 定制链接
}

codes = []
custom_cnt = 0
normal_cnt = 0
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
    l_int = int(round(l))
    w_int = int(round(w))
    h_int = int(round(h))
    km_code = f'{l_int}*{w_int}*{h_int}-{dim_kind}-{material}'
    codes.append((shop, prod_id, spec_id, km_code))
    normal_cnt += 1

print(f'正常编码: {normal_cnt}, 定制链接: {custom_cnt}, 解析失败(当定制): {noparse_cnt}')

# ===== 写入 Excel =====
outpath = r'D:\Desktop\换绑_东莞市新鑫星包装材料有限公司.xlsx'
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

print(f'✅ 已生成: {outpath}, 共 {len(codes)} 条')
