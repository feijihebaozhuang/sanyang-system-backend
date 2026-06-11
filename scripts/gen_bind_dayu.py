# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市大鱼包装材料有限公司'

print('读取中...')
df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(shop_data)} 条')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# ===== 解析器 =====
def p_lw_h_cm(s):
    """长宽【NxNcm】；高【Ncm】"""
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'高[度]?\s*【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p_lw_h_cm_rev(s):
    """高度【Ncm】;长宽【NxNcm】"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p_lw_h_bracket(s):
    """【N个】高度【Ncm】;长宽【NxNcm】"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p_lw_cm_h_cm_bracket(s):
    """长宽【NxNcm】；【N个】高【Ncm】"""
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'高[度]?【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p8_9_10_11(s):
    """高度【Ncm特硬xxx】;长宽【NxN】cm"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p12_13(s):
    """高度【Ncm特硬xxx】内径;长宽【NxN】cm内径尺寸"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p14(s):
    """高度【Ncm】黄色外径【N个】;长宽【NxNcm】"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p15_zhixiang(s):
    """N个长宽N*N；高N【N层】→ 纸箱"""
    m = re.search(r'长宽\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'高\s*(\d[\d.]*)\s*【(\d+)层】', s)
    if not m: return None
    h = float(m.group(1))
    layer = int(m.group(2))
    return (l, w, h, layer)

def p16_17(s):
    """高【Ncm】黄色内径;长宽【NxNcm】N个 / 高度【Ncm】黄色外径;长宽【NxNcm】N个"""
    m = re.search(r'高[度]?【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p18(s):
    """高度【Ncm】黄色外径N个*长宽【NxNcm】"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p19_20(s):
    """长宽【NxNcm】；高【Ncm】黄色内/外径【N个】"""
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'高[度]?【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p21(s):
    """长Ncm【N个】；宽-高【N*Ncm】外径"""
    m = re.search(r'长\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    m = re.search(r'宽-高【\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    return (l, w, h)

def p22(s):
    """长宽【NxN】cm；高度【Ncm】；黑色N个一组"""
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p23_30(s):
    """长宽【NxNcm】；高度【Ncm】【内/外径N个】"""
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p24_25(s):
    """高度【Ncm超硬xxx】内/外径;长宽【NxN】cm"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p26(s):
    """长宽【NxNcm】；【N个】高度【Ncm】黄色内径（小尺寸版）"""
    return p_lw_cm_h_cm_bracket(s)

def p27(s):
    """长宽【NxNcm】；高度【Ncm】黄色内径【N个】"""
    return p19_20(s)

def p28(s):
    """长宽【NxNcm】；高度【Ncm】黄色外径N个"""
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p29(s):
    """高度【Ncm】黄色内径N个*长宽【NxNcm】"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p31_32(s):
    """长宽【NxNm】；【N个】高【Ncm】黄色外/内径（单位m=cm写法）"""
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*m', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'高【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p33(s):
    """高度【Ncm】黄色内径*长宽【NxNcm】"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p34(s):
    """长宽【NxNm】；高度【Ncm】黄色外径N个"""
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*m', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p35(s):
    """高度【Ncm】黄色内径N个;长宽【NxNm】"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*m', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p36(s):
    """高度【Ncm】黄色外径;长宽【NxNm】【N个】"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*m', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p37(s):
    """长宽【NxNm】；高度【Ncm】【内径N个】"""
    return p34(s)

def p38(s):
    """高度【Ncm】黄色外径;长宽【NxNcm】【N个】】"""
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p39_40(s):
    """高度【Ncm特硬xxx】内径;长宽【NxN】cm"""
    return p8_9_10_11(s)

# ===== 结构配置 =====
STRUCT_CONFIG = {
    '长宽【NxNcm】；【N个】高【Ncm】黄色内径;长宽【NxNcm】;【N个】高【Ncm】黄色内径': ('内径', '特硬', p_lw_cm_h_cm_bracket),
    '长宽【NxNcm】；【N个】高【Ncm】黄色外径;长宽【NxNcm】;【N个】高【Ncm】黄色外径': ('外径', '特硬', p_lw_cm_h_cm_bracket),
    '【N个】高度【Ncm】黄色内径;长宽【NxNcm】': ('内径', '特硬', p_lw_h_bracket),
    '长宽【NxNcm】；【N个】高度【Ncm】黄色外径;长宽【NxNcm】;【N个】高度【Ncm】黄色外径': ('外径', '特硬', p_lw_cm_h_cm_bracket),
    '高度【Ncm】黄色外径;长宽【NxNcm】【N个】;高度【Ncm】黄色外径': ('外径', '特硬', p_lw_h_cm_rev),
    '高度【Ncm】黄色内径N个;长宽【NxNcm】;高度【Ncm】黄色内径N个': ('内径', '特硬', p_lw_h_cm_rev),
    '【N个】高度【Ncm】黄色外径;长宽【NxNcm】;【N个】高度【Ncm】黄色外径': ('外径', '特硬', p_lw_h_bracket),
    '高度【Ncm特硬白色】;长宽【NxN】cm;高度【Ncm特硬白色】': ('外径', '白色', p8_9_10_11),
    '高度【Ncm特硬黄】;长宽【NxN】cm;高度【Ncm特硬黄】': ('外径', '特硬', p8_9_10_11),
    '高度【Ncm超硬台湾纸】内径;长宽【NxN】cm;高度【Ncm超硬台湾纸】内径': ('内径', '超硬', p8_9_10_11),
    '高度【Ncm超硬台湾纸】外径;长宽【NxN】cm;高度【Ncm超硬台湾纸】外径': ('外径', '超硬', p8_9_10_11),
    '高度【Ncm特硬白色】内径;长宽【NxN】cm内径尺寸;高度【Ncm特硬白色】内径': ('内径', '白色', p12_13),
    '高度【Ncm特硬黄】内径;长宽【NxN】cm内径尺寸;高度【Ncm特硬黄】内径': ('内径', '特硬', p12_13),
    '高度【Ncm】黄色外径【N个】;长宽【NxNcm】;高度【Ncm】黄色外径【N个】': ('外径', '特硬', p14),
    # 15: 纸箱 - 特殊处理
    'N个长宽N*N；高N【N层】;N个长宽N*N;高N【N层】': ('纸箱', None, p15_zhixiang),
    '高【Ncm】黄色内径;长宽【NxNcm】N个': ('内径', '特硬', p16_17),
    '高度【Ncm】黄色外径;长宽【NxNcm】N个': ('外径', '特硬', p16_17),
    '高度【Ncm】黄色外径N个*长宽【NxNcm】;长宽【NxNcm】;高度【Ncm】黄色外径N个': ('外径', '特硬', p18),
    '长宽【NxNcm】；高【Ncm】黄色内径【N个】;长宽【NxNcm】;高【Ncm】黄色内径【N个】': ('内径', '特硬', p19_20),
    '长宽【NxNcm】；高【Ncm】黄色外径【N个】;长宽【NxNcm】;高【Ncm】黄色外径【N个】': ('外径', '特硬', p19_20),
    '长Ncm【N个】；宽-高【N*Ncm】外径;长Ncm【N个】;宽-高【N*Ncm】外径': ('外径', '特硬', p21),
    '长宽【NxN】cm；高度【Ncm】；黑色N个一组;长宽【NxN】cm;高度【Ncm】;黑色N个一组': ('外径', '黑色', p22),
    '长宽【NxNcm】；高度【Ncm】【内径N个】;长宽【NxNcm】;高度【Ncm】【内径N个】': ('内径', '特硬', p23_30),
    '高度【Ncm超硬白色】内径;长宽【NxN】cm': ('内径', '白色', p24_25),
    '高度【Ncm超硬白色】外径;长宽【NxN】cm': ('外径', '白色', p24_25),
    '长宽【NxNcm】；【N个】高度【Ncm】黄色内径;长宽【NxNcm】;【N个】高度【Ncm】黄色内径': ('内径', '特硬', p26),
    '长宽【NxNcm】；高度【Ncm】黄色内径【N个】;长宽【NxNcm】;高度【Ncm】黄色内径【N个】': ('内径', '特硬', p27),
    '长宽【NxNcm】；高度【Ncm】黄色外径N个;长宽【NxNcm】;高度【Ncm】黄色外径N个': ('外径', '特硬', p28),
    '高度【Ncm】黄色内径N个*长宽【NxNcm】;长宽【NxNcm】;高度【Ncm】黄色内径N个': ('内径', '特硬', p29),
    '长宽【NxNcm】；高度【Ncm】【外径N个】;长宽【NxNcm】;高度【Ncm】【外径N个】': ('外径', '特硬', p23_30),
    '长宽【NxNm】；【N个】高【Ncm】黄色外径;长宽【NxNm】;【N个】高【Ncm】黄色外径': ('外径', '特硬', p31_32),
    '长宽【NxNm】；【N个】高【Ncm】黄色内径;长宽【NxNm】;【N个】高【Ncm】黄色内径': ('内径', '特硬', p31_32),
    '高度【Ncm】黄色内径*长宽【NxNcm】;长宽【NxNcm】;高度【Ncm】黄色内径': ('内径', '特硬', p33),
    '长宽【NxNm】；高度【Ncm】黄色外径N个;长宽【NxNm】;高度【Ncm】黄色外径N个': ('外径', '特硬', p34),
    '高度【Ncm】黄色内径N个;长宽【NxNm】;高度【Ncm】黄色内径N个': ('内径', '特硬', p35),
    '高度【Ncm】黄色外径;长宽【NxNm】【N个】;高度【Ncm】黄色外径': ('外径', '特硬', p36),
    '长宽【NxNm】；高度【Ncm】【内径N个】;长宽【NxNm】;高度【Ncm】【内径N个】': ('内径', '特硬', p37),
    '高度【Ncm】黄色外径;长宽【NxNcm】【N个】】;高度【Ncm】黄色外径': ('外径', '特硬', p38),
    '高度【Ncm特硬白色】内径;长宽【NxN】cm;高度【Ncm特硬白色】内径': ('内径', '白色', p39_40),
    '高度【Ncm特硬黄】内径;长宽【NxN】cm;高度【Ncm特硬黄】内径': ('内径', '特硬', p39_40),
}

codes = []
normal_cnt = 0
custom_cnt = 0
zhixiang_cnt = 0
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
    
    if dim_kind == '纸箱':
        dims = parser(spec)
        if dims is None or len(dims) != 4:
            codes.append((shop, prod_id, spec_id, '定制链接'))
            noparse_cnt += 1
            continue
        l, w, h, layer = dims
        l_int = max(1, int(round(l)))
        w_int = max(1, int(round(w)))
        h_int = max(1, int(round(h)))
        km_code = f'{l_int}*{w_int}*{h_int}-EB'
        codes.append((shop, prod_id, spec_id, km_code))
        zhixiang_cnt += 1
        continue
    
    if dim_kind == '定制':
        codes.append((shop, prod_id, spec_id, '定制链接'))
        custom_cnt += 1
        continue
    
    parser_fn = parser
    dims = parser_fn(spec)
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

print(f'正常飞机盒: {normal_cnt}, 纸箱: {zhixiang_cnt}, 定制链接: {custom_cnt}, 解析失败: {noparse_cnt}, 合计: {len(codes)}')

outpath = r'D:\Desktop\换绑_深圳市大鱼包装材料有限公司.xlsx'
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
