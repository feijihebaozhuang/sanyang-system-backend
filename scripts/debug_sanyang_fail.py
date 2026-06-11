# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import defaultdict

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市三羊包装材料有限公司'

df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

def p_lw_dim(s):
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】\s*(cm)?', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【?\s*([\d.]+)\s*cm\s*高】?', s)
    if not m:
        m = re.search(r'([\d.]+)\s*cm\s*高', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p_lw_dim_cm(s):
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【\s*([\d.]+)\s*cm\s*高】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p8(s):
    m = re.search(r'【长\*宽】\s*([\d.]+)\s*\*\s*([\d.]+)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【高】\s*([\d.]+)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p9_10(s):
    m = re.search(r'宽高\s*([\d.]+)\s*\*\s*([\d.]+)', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长\s*([\d.]+)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p15_16(s):
    m = re.search(r'外尺寸【长\*宽】\s*([\d.]+)\s*\*\s*([\d.]+)', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【高】\s*([\d.]+)\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p24(s):
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【【\s*([\d.]+)\s*cm\s*高】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p25(s):
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【外尺寸】\s*【\s*([\d.]+)\s*cm\s*高】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p26(s):
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【\s*([\d.]+)\s*cm\s*高】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

def p27(s):
    m = re.search(r'长\*宽【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】c', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    m = re.search(r'【\s*([\d.]+)\s*cm\s*高】', s)
    if not m: return None
    h = float(m.group(1))
    return (l, w, h)

PARSERS = {
    0: ('外径', '特硬', p_lw_dim),
    1: ('外径', '白色', p_lw_dim),
    2: ('内径', '特硬', p_lw_dim),
    3: ('内径', '白色', p_lw_dim_cm),
    4: ('内径', '特硬', p_lw_dim),
    5: ('外径', '白色', p_lw_dim),
    6: ('外径', '白色', p_lw_dim),
    7: ('外径', '特硬', p8),
    8: ('外径', '特硬', p9_10),
    9: ('外径', '白色', p9_10),
    10: ('外径', '白色', p_lw_dim),
    11: ('内径', '白色', p_lw_dim),
    12: ('内径', '特硬', p_lw_dim),
    13: ('外径', '特硬', p_lw_dim),
    14: ('定制', None, None),
    15: ('外径', '黑色', p15_16),
    16: ('外径', '白色', p_lw_dim),
    17: ('外径', '超硬', p_lw_dim),
    18: ('内径', '特硬', p_lw_dim),
    19: ('内径', '超硬', p_lw_dim),
    20: ('定制', None, None),
    21: ('外径', '黑色', p_lw_dim),
    22: ('内径', '特硬', p_lw_dim),
    23: ('外径', '特硬', p24),
    24: ('外径', '特硬', p25),
    25: ('外径', '特硬', p26),
    26: ('内径', '特硬', p27),
    27: ('定制', None, None),
}

SKELETONS = [
    '长*宽【N*N】cm；外尺寸N级特硬原色；【Ncm高】;长*宽【N*N】cm;外尺寸N级特硬原色;【Ncm高】',
    '长*宽【N*N】；外尺寸特硬双面白；【Ncm高】;长*宽【N*N】;外尺寸特硬双面白;【Ncm高】',
    '长*宽【N*N】；外尺寸特硬原色；【Ncm高】;长*宽【N*N】;外尺寸特硬原色;【Ncm高】',
    '长*宽【N*N】cm;外尺寸白色【Ncm高】',
    '长*宽【N*N】；外尺寸N级特硬原色；【Ncm高】;长*宽【N*N】;外尺寸N级特硬原色;【Ncm高】',
    '长*宽【N*N】；外尺寸特硬双面白色；【Ncm高】;长*宽【N*N】;外尺寸特硬双面白色;【Ncm高】',
    '长*宽【N*N】cm；外尺寸特硬双面白色；【Ncm高】;长*宽【N*N】cm;外尺寸特硬双面白色;【Ncm高】',
    '特硬牛皮色【长*宽】N*N;【高】NcmN个一组',
    '宽高N*N（牛皮色）;长NcmSN级硬度',
    '宽高N*N（白色）;长NcmSN级硬度',
    '长*宽【N*N】；外尺寸N级特硬双面白；Ncm高;长*宽【N*N】;外尺寸N级特硬双面白;Ncm高',
    '长*宽【N*N】；内寸N级特硬双面白；Ncm高;长*宽【N*N】;内寸N级特硬双面白;Ncm高',
    '长*宽【N*N】；内寸N级特硬原色；Ncm高;长*宽【N*N】;内寸N级特硬原色;Ncm高',
    '长*宽【N*N】；外尺寸N级特硬原色；Ncm高;长*宽【N*N】;外尺寸N级特硬原色;Ncm高',
    '外尺寸【长*宽】N*N;【高】Ncm红色',
    '外尺寸【长*宽】N*N;【高】Ncm黑色',
    '长*宽【N*N】；外尺寸N级特硬双面白；【Ncm高】;长*宽【N*N】;外尺寸N级特硬双面白;【Ncm高】',
    '长*宽【N*N】；外尺寸N级超硬原色；【Ncm高】;长*宽【N*N】;外尺寸N级超硬原色;【Ncm高】',
    '长*宽【N*N】；内寸N级特硬原色；【Ncm高】;长*宽【N*N】;内寸N级特硬原色;【Ncm高】',
    '长*宽【N*N】；内寸N级超硬原色；【Ncm高】;长*宽【N*N】;内寸N级超硬原色;【Ncm高】',
    '长*宽【N*N】cm；外尺寸【双面红】；【Ncm高】;长*宽【N*N】cm;外尺寸【双面红】;【Ncm高】',
    '长*宽【N*N】cm；外尺寸【双面黑】；【Ncm高】;长*宽【N*N】cm;外尺寸【双面黑】;【Ncm高】',
    '长*宽【N*N】；外尺寸N级特硬原色；【N高】;长*宽【N*N】;外尺寸N级特硬原色;【N高】',
    '长*宽【N*N】cm；外尺寸N级特硬原色；【【Ncm高】;长*宽【N*N】cm;外尺寸N级特硬原色;【【Ncm高】',
    '长*宽【N*N】cm；外尺寸N级特硬原色；【外尺寸】【Ncm高】特硬牛皮色;长*宽【N*N】cm;外尺寸N级特硬原色;【外尺寸】【Ncm高】特硬牛皮色',
    '长*宽【N*Ncm；外尺寸N级特硬原色；【Ncm高】;长*宽【N*Ncm;外尺寸N级特硬原色;【Ncm高】',
    '长*宽【N*N】c；外尺寸特硬原色；【Ncm高】;长*宽【N*N】c;外尺寸特硬原色;【Ncm高】',
    '特硬;飞机盒',
]

sk_map = {sk: i for i, sk in enumerate(SKELETONS)}

failed = []
for idx in range(len(shop_data)):
    spec = str(shop_data.iloc[idx]['平台规格名称'] or '').strip()
    sk = make_skeleton(spec)
    pos = sk_map.get(sk)
    if pos is None:
        continue
    cfg = PARSERS.get(pos)
    if cfg is None:
        continue
    dim_kind, material, parser = cfg
    if dim_kind == '定制':
        continue
    
    # 只测试第一个失败的位置
    r = parser(spec)
    if r is None:
        if len(failed) < 5:
            failed.append((pos, sk, spec))
            print(f'❌ idx={pos}: {sk}')
            print(f'   例: {spec[:130]}')

if not failed:
    print('✅ 所有都正常')
