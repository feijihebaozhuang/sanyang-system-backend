# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '飞机盒止合专卖店'

print('读取中...')
df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(shop_data)} 条')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# ===== 解析器 =====
def general_parse(s):
    """高度Ncm + 长x宽【NxNcm】"""
    m = re.search(r'高度\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*[xX×]\s*宽[【\[]?\s*([\d.]+)\s*[xX×]\s*([\d.]+)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def parse_wh_len(s):
    """宽*高【N*Ncm】; 长度【Ncm】"""
    m = re.search(r'宽\s*\*\s*高[【\[]\s*([\d.]+)\s*\*\s*([\d.]+)\s*cm[】\]]', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度[【\[]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def parse_cm_first(s):
    """高度cmN (高度cm2 即高度=2) + 长x宽【NxNcm】"""
    m = re.search(r'高度[cm着]*\s*(\d[\d.]*)', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*[xX×]\s*宽[【\[]?\s*([\d.]+)\s*[xX×]\s*([\d.]+)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

# ===== 结构配置 =====
STRUCT_CONFIG = {
    'N级进口特硬【高度Ncm】;N层;飞机盒内径-/长x宽【NxNcm】': ('内径', '特硬', general_parse),
    'N级进口特硬【高度Ncm】单个装;N层;飞机盒外径-/长x宽【NxNcm】': ('外径', '特硬', general_parse),
    'N级进口特硬【高度Ncm】单个装;N层;飞机盒外径-/长x宽【NxNcm】;台湾【超硬黄】': ('外径', '超硬', general_parse),
    'N级进口特硬【高度Ncm】单个装;N层;飞机盒外径-/长x宽【NxNcm】;暗钻【特硬黑】': ('外径', '黑色', general_parse),
    'N级进口特硬【高度Ncm】单个装;N层;飞机盒外径-/长x宽【NxNcm】;烈焰【特硬红】': ('定制', None, None),
    'N级进口特硬【高度Ncm】单个装;N层;飞机盒外径-/长x宽【NxNcm】;精美【特硬白】': ('外径', '白色', general_parse),
    'N级进口特硬-/宽*高【N*Ncm】;N层;飞机盒长度【Ncm】/N个一捆;特硬【双面白】': ('外径', '白色', parse_wh_len),
    'N级进口特硬-/宽*高【N*Ncm】;N层;飞机盒长度【Ncm】/N个一捆;特硬【双面红】': ('定制', None, None),
    'N级进口特硬-/宽*高【N*Ncm】;N层;飞机盒长度【Ncm】/N个一捆;特硬【双面黑】': ('外径', '黑色', parse_wh_len),
    'N级进口特硬-/宽*高【N*Ncm】;N层;飞机盒长度【Ncm】/N个一捆': ('外径', '特硬', parse_wh_len),
    '可定做异型图形;其他;长*宽【N*N】mm': ('定制', None, None),
    '定做N元专拍链接;其他;长*宽【N*N】mm': ('定制', None, None),
    '需要更多规格可咨询客服;其他;长*宽【N*N】mm': ('定制', None, None),
    'N级超硬牛卡【高度Ncm】;N层;飞机盒内径-/长x宽【NxNcm】': ('内径', '超硬', general_parse),
    'N级超硬牛卡【高度Ncm】;N层;飞机盒外径-/长x宽【NxNcm】': ('外径', '超硬', general_parse),
    'N级特硬普卡【高度Ncm】;N层;飞机盒内径-/长x宽【NxNcm】': ('内径', '特硬', general_parse),
    'N级特硬普卡【高度Ncm】;N层;飞机盒外径-/长x宽【NxNcm】': ('外径', '特硬', general_parse),
    'N级特硬普卡【高度cmN】;N层;飞机盒内径-/长x宽【NxNcm】': ('内径', '特硬', parse_cm_first),
    'N级特硬普卡【高度cmN】;N层;飞机盒外径-/长x宽【NxNcm】': ('外径', '特硬', parse_cm_first),
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
    l_int = int(round(l))
    w_int = int(round(w))
    h_int = int(round(h))
    km_code = f'{l_int}*{w_int}*{h_int}-{dim_kind}-{material}'
    codes.append((shop, prod_id, spec_id, km_code))
    normal_cnt += 1

print(f'正常编码: {normal_cnt}, 定制链接: {custom_cnt}, 解析失败(当定制): {noparse_cnt}, 合计: {len(codes)}')

outpath = r'D:\Desktop\换绑_飞机盒止合专卖店.xlsx'
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
