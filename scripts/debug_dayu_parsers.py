# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import defaultdict

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市大鱼包装材料有限公司'

df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# collect all specs per skeleton
skeleton_specs = defaultdict(list)
for idx in range(len(shop_data)):
    spec = str(shop_data.iloc[idx]['平台规格名称'] or '').strip()
    sk = make_skeleton(spec)
    if len(skeleton_specs[sk]) < 2:
        skeleton_specs[sk].append(spec)

# ===== parsers (copy from gen_bind_dayu.py) =====
def p_lw_cm_h_cm_bracket(s):
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p_lw_h_bracket(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p_lw_h_cm_rev(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p8_9_10_11(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p12_13(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p14(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p15_zhixiang(s):
    m = re.search(r'长宽\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高\s*(\d[\d.]*)\s*【(\d+)层】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p16_17(s):
    m = re.search(r'高[度]?【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p18(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p19_20(s):
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p21(s):
    m = re.search(r'长\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    m = re.search(r'宽-高【\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    return (l, w, h)

def p22(s):
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p23_30(s):
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p24_25(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*】\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p26(s): return p_lw_cm_h_cm_bracket(s)
def p27(s): return p19_20(s)

def p28(s):
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p29(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p31_32(s):
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*m', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p33(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p34(s):
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*m', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p35(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*m', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p36(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*m', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p37(s): return p34(s)

def p38(s):
    m = re.search(r'高度【\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*【\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p39_40(s): return p8_9_10_11(s)

PARSER_MAP = {
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

# test each skeleton
for sk, specs in skeleton_specs.items():
    cfg = PARSER_MAP.get(sk)
    if cfg is None:
        continue
    dim_kind, material, parser = cfg
    for i, spec in enumerate(specs):
        r = parser(spec)
        if r is None:
            tag = '首行' if i == 0 else '次行'
            print(f'❌ {tag}失败: {sk}')
            print(f'    规格: {spec[:120]}')
