# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '飞机盒小批量专卖店'

print('读取中...')
df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
shop_data = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(shop_data)} 条')

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# ===== 解析器 =====
def p1_2(s):
    """宽N高Ncm;长度Ncm【N个】白色/超硬黄色"""
    m = re.search(r'宽\s*(\d[\d.]*)\s*高\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p3(s):
    """宽【Ncm】高【Ncm】;【N个】长度【Ncm】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)cm】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p4(s):
    """宽【Ncm】高【Ncm】白色;【N个】长度【Ncm】"""
    return p3(s)

def p5_6(s):
    """宽【Ncm】高【Ncm】白色/内径;【N个】长度【Ncm】【内径】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)cm】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p7(s):
    """宽N高NCM;长度NCM【N个】超硬黄色"""
    m = re.search(r'宽\s*(\d[\d.]*)\s*高\s*(\d[\d.]*)\s*CM', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度\s*(\d[\d.]*)\s*CM', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p8_12(s):
    """N×N×N 或 N×N×Nmm"""
    m = re.search(r'(\d[\d.]*)\s*[×*xX]\s*(\d[\d.]*)\s*[×*xX]\s*(\d[\d.]*)', s)
    if not m: return None
    vals = sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True)
    # 判断单位：如果规格名中有mm且数值>=100，转cm
    l, w, h = vals
    if 'mm' in s and l >= 100:
        l /= 10; w /= 10; h /= 10
    return (l, w, h)

def p14(s):
    """宽【Ncm】高【Ncm】【内径】;【N个】长度【Nm】【内径】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)m】', s)
    if not m: return None
    l = float(m.group(1))  # m 单位
    return (l, w, h)

def p15(s):
    """宽【Ncm】高【Ncm】内径;【N个】长【Nm】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长【(\d[\d.]*)m】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p17(s):
    """黄色-高度N高度cm内径【N个】;长宽NxNcm内尺寸"""
    m = re.search(r'高度\s*(\d[\d.]*)\s*高度\s*cm', s)
    if not m: return None
    h = float(m.group(1))
    m = re.search(r'长[宽度]*\s*(\d[\d.]*)\s*[xX×]\s*(\d[\d.]*)\s*cm', s)
    if not m: return None
    l, w = float(m.group(1)), float(m.group(2))
    return (l, w, h)

def p18(s):
    """宽【Nm】高【Ncm】白色;【N个】长度【Ncm】"""
    m = re.search(r'宽【(\d[\d.]*)m】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)cm】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p19_20(s):
    """宽【Ncm】高【Ncm】白色/内径;【N个】长度【Nm】【内径】/【Ncm】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)(cm|m)】', s)
    if not m: return None
    l = float(m.group(1))
    if m.group(2) == 'm':
        pass  # 已经是m
    return (l, w, h)

def p21(s):
    """宽【Ncm】高【Ncm】白色;【N个】长度【Nm】"""
    return p19_20(s)

def p22_25(s):
    """宽【Nm】高【Ncm】;【N个】长/长度【Ncm/Nm】"""
    m = re.search(r'宽【(\d[\d.]*)m】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'[长长度]+【(\d[\d.]*)(cm|m)】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p23(s):
    """宽【Ncm】高【Ncm【内径】;【N个】长度【Ncm】【内径】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)cm】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p24(s):
    """宽【Ncm】高【Ncm】;【N个】长度【Nm】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)m】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p26(s):
    """宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】径】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)cm】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p27(s):
    """宽【Ncm】高【Ncm】白色个;【N个】长度【Ncm】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)cm】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p28(s):
    """宽【Nm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】"""
    m = re.search(r'宽【(\d[\d.]*)m】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)cm】', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p29(s):
    """宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm【内径】】"""
    m = re.search(r'宽【(\d[\d.]*)cm】高【(\d[\d.]*)cm】', s)
    if not m: return None
    w = float(m.group(1)); h = float(m.group(2))
    m = re.search(r'长度【(\d[\d.]*)cm', s)
    if not m: return None
    l = float(m.group(1))
    return (l, w, h)

def p30_40_star(s):
    """N*N**N 或 N**N*Ncm 格式"""
    m = re.search(r'(\d[\d.]*)\s*\*+\s*(\d[\d.]*)\s*\*+\s*(\d[\d.]*)', s)
    if not m: return None
    vals = sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True)
    l, w, h = vals
    return (l, w, h)

def p33_35(s):
    """N*N*N"""
    m = re.search(r'(\d[\d.]*)\s*\*\s*(\d[\d.]*)\s*\*\s*(\d[\d.]*)', s)
    if not m: return None
    vals = sorted([float(m.group(1)), float(m.group(2)), float(m.group(3))], reverse=True)
    return (vals[0], vals[1], vals[2])

def p36_38(s):
    """N*N"""
    m = re.search(r'(\d[\d.]*)\s*\*\s*(\d[\d.]*)', s)
    if not m: return None
    l = float(m.group(1)); w = float(m.group(2))
    # 无高时，按你的标注，用同一数值的高
    return (l, w, 0)  # 需要标注者的高

# ===== 结构配置 =====
STRUCT_CONFIG = {
    '宽N高Ncm;长度Ncm【N个】白色': ('外径', '白色', p1_2),
    '宽N高Ncm;长度Ncm【N个】超硬黄色': ('外径', '超硬', p1_2),
    '宽【Ncm】高【Ncm】;【N个】长度【Ncm】': ('外径', '特硬', p3),
    '宽【Ncm】高【Ncm】白色;【N个】长度【Ncm】': ('外径', '白色', p4),
    '宽【Ncm】高【Ncm】白色;【N个】长度【Ncm】【内径】': ('内径', '白色', p5_6),
    '宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】': ('内径', '特硬', p5_6),
    '宽N高NCM;长度NCM【N个】超硬黄色': ('外径', '超硬', p7),
    '黄色优质特硬【N个】挑战性价比;N×N×N': ('外径', '特硬', p8_12),
    '高档超硬【双面白】N个;N×N×N': ('外径', '白色', p8_12),
    '双面纯色【N个】黑&红;N×N×N': ('定制', None, None),
    '黄色优质特硬【N个】挑战性价比;N×N×Nmm': ('外径', '特硬', p8_12),
    '高档超硬【双面白】N个;N×N×Nmm': ('外径', '白色', p8_12),
    '双面纯色【N个】黑&红;N×N×Nmm': ('定制', None, None),
    '宽【Ncm】高【Ncm】【内径】;【N个】长度【Nm】【内径】': ('内径', '特硬', p14),
    '宽【Ncm】高【Ncm】内径;【N个】长【Nm】': ('内径', '特硬', p15),
    '【外尺寸正方形】【内外尺寸长方形飞机盒】【其他链接】;长宽NxNcm内尺寸': ('定制', None, None),
    '黄色-高度N高度cm内径【N个】;长宽NxNcm内尺寸': ('内径', '特硬', p17),
    '宽【Nm】高【Ncm】白色;【N个】长度【Ncm】': ('外径', '白色', p18),
    '宽【Ncm】高【Ncm】白色;【N个】长度【Nm】【内径】': ('内径', '白色', p19_20),
    '宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】': ('内径', '特硬', p19_20),
    '宽【Ncm】高【Ncm】白色;【N个】长度【Nm】': ('外径', '白色', p21),
    '宽【Nm】高【Ncm】;【N个】长【Ncm】': ('外径', '特硬', p22_25),
    '宽【Ncm】高【Ncm【内径】;【N个】长度【Ncm】【内径】': ('内径', '特硬', p23),
    '宽【Ncm】高【Ncm】;【N个】长度【Nm】': ('外径', '特硬', p24),
    '宽【Nm】高【Ncm】;【N个】长度【Ncm】': ('外径', '特硬', p22_25),
    '宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】径】': ('内径', '特硬', p26),
    '宽【Ncm】高【Ncm】白色个;【N个】长度【Ncm】': ('外径', '白色', p27),
    '宽【Nm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】': ('内径', '特硬', p28),
    '宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm【内径】】': ('内径', '特硬', p29),
    '优质进口纸-黄色【N个】;N*N**N': ('外径', '特硬', p30_40_star),
    '双白色【N个】;N*N**N': ('外径', '白色', p30_40_star),
    '双面纯色【N个】黑&红;N*N**N': ('定制', None, None),
    '优质进口纸-黄色【N个】;N*N*N': ('外径', '特硬', p33_35),
    '双白色【N个】;N*N*N': ('外径', '白色', p33_35),
    '双面纯色【N个】黑&红;N*N*N': ('定制', None, None),
    '优质进口纸-黄色N个;N*N': ('外径', '特硬', p36_38),
    '双白色N个;N*N': ('外径', '白色', p36_38),
    '双面纯色【N个】黑&红;N*N': ('定制', None, None),
    '优质进口纸-黄色【N个】;N**N*Ncm': ('外径', '特硬', p30_40_star),
    '双白色【N个】;N**N*Ncm': ('外径', '白色', p30_40_star),
    '双面纯色【N个】黑&红;N**N*Ncm': ('定制', None, None),
    '双面黑色【N个】;超【大】飞机盒N-N厘米长度': ('定制', None, None),
    '双面黑色【N个】;超【小】飞机盒单位CM厘米': ('定制', None, None),
    '浅黄色【特硬N个】;超【大】飞机盒N-N厘米长度': ('定制', None, None),
    '浅黄色【特硬N个】;超【小】飞机盒单位CM厘米': ('定制', None, None),
    '高档【双面白色N个】;超【大】飞机盒N-N厘米长度': ('定制', None, None),
    '高档【双面白色N个】;超【小】飞机盒单位CM厘米': ('定制', None, None),
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
    
    # 对 N*N 格式（无高），用宽作为高
    if h == 0:
        h = w
    
    l_int = max(1, int(round(l)))
    w_int = max(1, int(round(w)))
    h_int = max(1, int(round(h)))
    km_code = f'{l_int}*{w_int}*{h_int}-{dim_kind}-{material}'
    codes.append((shop, prod_id, spec_id, km_code))
    normal_cnt += 1

print(f'正常编码: {normal_cnt}, 定制链接: {custom_cnt}, 解析失败(当定制): {noparse_cnt}, 合计: {len(codes)}')

outpath = r'D:\Desktop\换绑_飞机盒小批量专卖店.xlsx'
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
