# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '俊鑫纸品厂'

df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# 测试每个结构的第一个和最后一个spec
seen = {}
for idx in range(len(shop_data)):
    spec = str(shop_data.iloc[idx]['平台规格名称'] or '').strip()
    sk = make_skeleton(spec)
    if sk not in seen:
        seen[sk] = []

# 收集每个结构的原始数据
test_cases = {}
for idx in range(len(shop_data)):
    spec = str(shop_data.iloc[idx]['平台规格名称'] or '').strip()
    sk = make_skeleton(spec)
    if sk not in test_cases:
        test_cases[sk] = [spec, spec]
    else:
        test_cases[sk][1] = spec  # last one

# 定义所有解析器
def p_mm_bracket(s):
    m = re.search(r'【\s*([\d.]+)\s*[×*xX]\s*([\d.]+)\s*】\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    m = re.search(r'高【\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p_layer_height_len(s):
    m = re.search(r'【\s*(\d[\d.]*)\s*】\s*mm长【外径】', s)
    if not m: return None
    l = float(m.group(1))/10
    m = re.search(r'【\s*(\d[\d.]*)\s*】\s*mm宽', s)
    if not m: return None
    w = float(m.group(1))/10
    m = re.search(r'高【\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p_NxN_mm_height(s):
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
    m = re.search(r'【高(\d[\d.]*)】', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'([\d.]+)\s*[xX×]\s*([\d.]+)\s*x\s*高', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    return (l, w, h)

def p_color_cm(s):
    m = re.search(r'([\d.]+)\s*[xX×]\s*([\d.]+)\s*CM\s*【长[xX×]宽】', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    m = re.search(r'(\d[\d.]*)\s*CM\s*高度', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p_Nmm_height_NxNmm(s):
    m = re.search(r'(\d[\d.]*)\s*mm\s*【高】', s)
    if not m: return None
    h = float(m.group(1))/10
    m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*mm\s*【长\*宽】', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    return (l, w, h)

def p_mm_bracket_star(s):
    m = re.search(r'【\s*([\d.]+)\s*[×*xX]\s*([\d.]+)\s*】\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    m = re.search(r'【\s*(\d[\d.]*)\s*mm\s*】', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p_NxNmm_long_width(s):
    m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*mm\s*【长\*宽】', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    m = re.search(r'(\d[\d.]*)\s*mm\s*【高度】', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

def p_mm_bracket_no_close(s):
    m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*【长\*宽\s*mm', s)
    if not m: return None
    l = float(m.group(1))/10; w = float(m.group(2))/10
    m = re.search(r'高【\s*(\d[\d.]*)\s*mm', s)
    if not m: return None
    h = float(m.group(1))/10
    return (l, w, h)

PARSERS = {
    '内尺寸【产品尺寸拍这个】;【N*N】mm长-宽;高【Nmm】N个起发': p_mm_bracket,
    'N层;高【Nmm】N个起发;【N】mm长【外径】;【N】mm宽': p_layer_height_len,
    '内尺寸【产品尺寸】;N*N【长*宽mm】;高【Nmm】N个起发': p_NxN_mm_height,
    '外尺寸【盒子尺寸】;N*N【长*宽mm】;高【Nmm】N个起发': p_NxN_mm_height,
    '【高N】;NxNx高--厘米;内尺寸-产品尺寸': p_gaoN_x_cm,
    '【高N】;NxNx高--厘米;外尺寸-盒子尺寸': p_gaoN_x_cm,
    '外尺寸牛皮色【N个起发】;【N*N】mm长-宽;高【Nmm】N个起发': p_mm_bracket,
    '【高N】泰国黄【超硬】;NxNx高--厘米;内尺寸-产品尺寸': p_gaoN_x_cm,
    '【高N】泰国黄【超硬】;NxNx高--厘米;外尺寸-盒子尺寸': p_gaoN_x_cm,
    '外尺寸【盒子尺寸拍这个】;【N*N】mm长-宽;高【Nmm】N个起发': p_mm_bracket,
    '内尺寸【产品尺寸拍这个】;【N*N】mm长*宽;【Nmm】N起拍': p_mm_bracket_star,
    '外尺寸【盒子尺寸拍这个】;【N*N】mm长*宽;【Nmm】N起拍': p_mm_bracket_star,
    '内尺寸【产品尺寸】;N*Nmm【长*宽】;高【Nmm】N个起发': p_NxN_mm_height,
    '外尺寸【盒子尺寸】;N*Nmm【长*宽】;高【Nmm】N个起发': p_NxN_mm_height,
    '内尺寸【产品尺寸】;N*Nmm【长*宽】;Nmm【高度】': p_NxNmm_long_width,
    '外尺寸【盒子尺寸】;N*Nmm【长*宽】;Nmm【高度】': p_NxNmm_long_width,
    'N*Nmm【长*宽】;高【Nmm】N个起发;内尺寸【产品尺寸】': p_NxN_mm_height,
    'N*Nmm【长*宽】;高【Nmm】N个起发;外尺寸【盒子尺寸】': p_NxN_mm_height,
    'Nmm【高】N个起拍;N*Nmm【长*宽】;内尺寸【产品尺寸】': p_Nmm_height_NxNmm,
    'Nmm【高】N个起拍;N*Nmm【长*宽】;外尺寸【盒子尺寸】': p_Nmm_height_NxNmm,
    '白色;NxNCM【长x宽】超硬;NCM高度;飞机盒内尺寸': p_color_cm,
    '白色;NxNCM【长x宽】超硬;NCM高度;飞机盒外尺寸': p_color_cm,
    '黄色;NxNCM【长x宽】超硬;NCM高度;飞机盒内尺寸': p_color_cm,
    '黄色;NxNCM【长x宽】超硬;NCM高度;飞机盒外尺寸': p_color_cm,
    '内尺寸【产品尺寸】;N*N【长*宽mm;高【Nmm】N个起发': p_mm_bracket_no_close,
    '外尺寸【盒子尺寸】;N*N【长*宽mm;高【Nmm】N个起发': p_mm_bracket_no_close,
}

# 对每个骨架测试第一个和最后一个spec
for sk, (first_spec, last_spec) in sorted(test_cases.items()):
    parser = PARSERS.get(sk)
    if parser is None:
        print(f'⛔ 无配置: {sk}')
        print(f'     例: {first_spec[:80]}')
        continue
    r1 = parser(first_spec) if first_spec else None
    r2 = parser(last_spec) if last_spec != first_spec else None
    if r1 is None and r2 is None:
        ok1 = '✗' if r1 is None else f'{r1[0]:.0f}*{r1[1]:.0f}*{r1[2]:.0f}'
        ok2 = '✗' if r2 is None else f'{r2[0]:.0f}*{r2[1]:.0f}*{r2[2]:.0f}'
        print(f'❌ 均失败: {sk}')
        print(f'     例1: {first_spec[:100]}')
        if last_spec != first_spec:
            print(f'     例2: {last_spec[:100]}')
    elif r1 is None:
        print(f'⚠️  首失败: {sk}')
        print(f'     例1: {first_spec[:100]}')
