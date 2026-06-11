# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '俊鑫纸品厂'

print('读取中...')
df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(shop_data)} 条')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# ===== 解析器们 =====

def p_mm_bracket(s):
    """【N*N】mm...高【Nmm】"""
    m = re.search(r'【\s*([\d.]+)\s*[×*xX]\s*([\d.]+)\s*】\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    m = re.search(r'高【\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p_layer_height_len(s):
    """N层;高【Nmm】;【N】mm长【外径】;【N】mm宽"""
    m = re.search(r'【\s*(\d[\d.]*)\s*】\s*mm\s*长【外径】', s)
    if not m: return None
    l = float(m.group(1))/10
    m = re.search(r'【\s*(\d[\d.]*)\s*】\s*mm\s*宽', s)
    if not m: return None
    w = float(m.group(1))/10
    m = re.search(r'高【\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p_NxN_mm_height(s):
    """N*N【长*宽mm】;高【Nmm】 或 N*Nmm【长*宽】;高【Nmm】"""
    m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*(?:mm)?\s*【长\*宽', s)
    if not m:
        m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*mm\s*【长\*宽', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    m = re.search(r'高【\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p_gaoN_x_cm(s):
    """【高N】;NxNx高--厘米"""
    m = re.search(r'【高(\d[\d.]*)】', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'([\d.]+)\s*[xX×]\s*([\d.]+)\s*x\s*高', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p_color_cm(s):
    """白色/黄色;NxNCM【长x宽】;NCM高度"""
    m = re.search(r'([\d.]+)\s*[xX×]\s*([\d.]+)\s*CM\s*【长[xX×]宽】', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'(\d[\d.]*)\s*CM\s*高度', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p_Nmm_height_NxNmm(s):
    """Nmm【高】...N*Nmm【长*宽】"""
    m = re.search(r'(\d[\d.]*)\s*mm\s*【高】', s)
    if not m: return None
    h = float(m.group(1))/10
    m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*mm\s*【长\*宽】', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    return (l, w, h)

def p_mm_bracket_star(s):
    """内/外尺寸【xxx】;【N*N】mm长*宽;【Nmm】N起拍"""
    m = re.search(r'【\s*([\d.]+)\s*[×*xX]\s*([\d.]+)\s*】\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    m = re.search(r'【\s*(\d[\d.]*)\s*mm\s*】', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p_NxNmm_long_width(s):
    """N*Nmm【长*宽】;Nmm【高度】"""
    m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*mm\s*【长\*宽】', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    m = re.search(r'(\d[\d.]*)\s*mm\s*【高度】', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p_mm_bracket_no_close(s):
    """N*N【长*宽mm;高【Nmm】（缺少右括号的版本）"""
    m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*【长\*宽\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    m = re.search(r'高【\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

# ===== 结构配置 =====
STRUCT_CONFIG = {
    '内尺寸【产品尺寸拍这个】;【N*N】mm长-宽;高【Nmm】N个起发': ('内径', '特硬', p_mm_bracket),
    'N层;高【Nmm】N个起发;【N】mm长【外径】;【N】mm宽': ('外径', '特硬', p_layer_height_len),
    '内尺寸【产品尺寸】;N*N【长*宽mm】;高【Nmm】N个起发': ('内径', '特硬', p_NxN_mm_height),
    '外尺寸【盒子尺寸】;N*N【长*宽mm】;高【Nmm】N个起发': ('外径', '特硬', p_NxN_mm_height),
    '【高N】;NxNx高--厘米;内尺寸-产品尺寸': ('内径', '特硬', p_gaoN_x_cm),
    '【高N】;NxNx高--厘米;外尺寸-盒子尺寸': ('外径', '特硬', p_gaoN_x_cm),
    '外尺寸牛皮色【N个起发】;【N*N】mm长-宽;高【Nmm】N个起发': ('外径', '特硬', p_mm_bracket),
    '【高N】泰国黄【超硬】;NxNx高--厘米;内尺寸-产品尺寸': ('内径', '超硬', p_gaoN_x_cm),
    '【高N】泰国黄【超硬】;NxNx高--厘米;外尺寸-盒子尺寸': ('外径', '超硬', p_gaoN_x_cm),
    '外尺寸【盒子尺寸拍这个】;【N*N】mm长-宽;高【Nmm】N个起发': ('外径', '特硬', p_mm_bracket),
    '内尺寸【产品尺寸拍这个】;【N*N】mm长*宽;【Nmm】N起拍': ('内径', '特硬', p_mm_bracket_star),
    '外尺寸【盒子尺寸拍这个】;【N*N】mm长*宽;【Nmm】N起拍': ('外径', '特硬', p_mm_bracket_star),
    '内尺寸【产品尺寸】;N*Nmm【长*宽】;高【Nmm】N个起发': ('内径', '特硬', p_NxN_mm_height),
    '外尺寸【盒子尺寸】;N*Nmm【长*宽】;高【Nmm】N个起发': ('外径', '特硬', p_NxN_mm_height),
    '内尺寸【产品尺寸】;N*Nmm【长*宽】;Nmm【高度】': ('内径', '特硬', p_NxNmm_long_width),
    '外尺寸【盒子尺寸】;N*Nmm【长*宽】;Nmm【高度】': ('外径', '特硬', p_NxNmm_long_width),
    'N*Nmm【长*宽】;高【Nmm】N个起发;内尺寸【产品尺寸】': ('内径', '特硬', p_NxN_mm_height),
    'N*Nmm【长*宽】;高【Nmm】N个起发;外尺寸【盒子尺寸】': ('外径', '特硬', p_NxN_mm_height),
    'Nmm【高】N个起拍;N*Nmm【长*宽】;内尺寸【产品尺寸】': ('内径', '特硬', p_Nmm_height_NxNmm),
    'Nmm【高】N个起拍;N*Nmm【长*宽】;外尺寸【盒子尺寸】': ('外径', '特硬', p_Nmm_height_NxNmm),
    '白色;NxNCM【长x宽】超硬;NCM高度;飞机盒内尺寸': ('内径', '白色', p_color_cm),
    '白色;NxNCM【长x宽】超硬;NCM高度;飞机盒外尺寸': ('外径', '白色', p_color_cm),
    '黄色;NxNCM【长x宽】超硬;NCM高度;飞机盒内尺寸': ('内径', '超硬', p_color_cm),
    '黄色;NxNCM【长x宽】超硬;NCM高度;飞机盒外尺寸': ('外径', '超硬', p_color_cm),
    '内尺寸【产品尺寸拍这个】;还可以更长-问客服;高【Nmm】N个起发': ('定制', None, None),
    '外尺寸【盒子尺寸拍这个】;还可以更长-问客服;高【Nmm】N个起发': ('定制', None, None),
    '内尺寸【产品尺寸】;N*N【长*宽mm;高【Nmm】N个起发': ('内径', '特硬', p_mm_bracket_no_close),
    '外尺寸【盒子尺寸】;N*N【长*宽mm;高【Nmm】N个起发': ('外径', '特硬', p_mm_bracket_no_close),
    '特硬【双面白色】N个组;更多尺寸-详情N款现模;其他省外【偏远除外】': ('定制', None, None),
    '特硬【双面白色】N个组;更多尺寸-详情N款现模;广东省': ('定制', None, None),
    '黄色【日本牛卡】N个组;更多尺寸-详情N款现模;其他省外【偏远除外】': ('定制', None, None),
    '黄色【日本牛卡】N个组;更多尺寸-详情N款现模;广东省': ('定制', None, None),
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
    # 转成整数cm（四舍五入）
    l_int = max(1, int(round(l)))
    w_int = max(1, int(round(w)))
    h_int = max(1, int(round(h)))
    km_code = f'{l_int}*{w_int}*{h_int}-{dim_kind}-{material}'
    codes.append((shop, prod_id, spec_id, km_code))
    normal_cnt += 1

print(f'正常编码: {normal_cnt}, 定制链接: {custom_cnt}, 解析失败(当定制): {noparse_cnt}, 合计: {len(codes)}')

outpath = r'D:\Desktop\换绑_俊鑫纸品厂.xlsx'
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
