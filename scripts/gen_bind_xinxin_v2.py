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

# ===== 解析尺寸 =====
def clean_num(v):
    v = str(v).strip()
    parts = v.split('.')
    return parts[0] + '.' + ''.join(parts[1:]) if len(parts) > 2 else v

def to_cm(v_str):
    v_str = str(v_str).strip().lower()
    m = re.match(r'([\d.]+)\s*(mm|cm|m|厘米|毫米|米)?', v_str)
    if not m: return None
    v = m.group(1); unit = m.group(2) or ''
    try: v = float(clean_num(v))
    except: return None
    if unit in ('mm','毫米'): v /= 10.0
    elif unit in ('m','米'): v *= 100
    return round(v, 2)

def extract_lwh(s):
    l = w = h = None
    # 长宽【NxN】cm；高度【Ncm...】
    m = re.search(r'长[度]?\s*[：:＝=]?\s*([\d.]+(?:\s*(?:cm|mm|m|厘米|毫米|米))?)', s)
    if m: l = to_cm(m.group(1))
    m = re.search(r'宽[度]?\s*[：:＝=]?\s*([\d.]+(?:\s*(?:cm|mm|m|厘米|毫米|米))?)', s)
    if m: w = to_cm(m.group(1))
    m = re.search(r'高[度]?\s*[：:＝=]?\s*([\d.]+(?:\s*(?:cm|mm|m|厘米|毫米|米))?)', s)
    if m: h = to_cm(m.group(1))
    if l and w and h: return (l, w, h)
    # 长宽【NxN】
    m = re.search(r'长[宽度]?\s*[【\[]\s*([\d.]+)\s*[×*xX]\s*([\d.]+)\s*[】\]]', s)
    if m:
        if not l: l = to_cm(m.group(1))
        if not w: w = to_cm(m.group(2))
    # 高【Ncm...】
    m = re.search(r'高[度]?\s*[【\[]\s*([\d.]+)\s*(?:cm|厘米)?\s*[】\]]', s)
    if m and not h: h = to_cm(m.group(1))
    if l and w and h: return (l, w, h)
    # N CM；宽Ncm；高Ncm
    m = re.match(r'([\d.]+)\s*CM[；;]\s*宽\s*([\d.]+)\s*cm[；;]\s*高\s*([\d.]+)\s*cm', s, re.I)
    if m:
        l = to_cm(m.group(1)); w = to_cm(m.group(2)); h = to_cm(m.group(3))
        return (l, w, h)
    # N*N*N
    m = re.search(r'([\d.]+)\s*[×*xX]\s*([\d.]+)\s*[×*xX]\s*([\d.]+)', s)
    if m:
        vals = sorted([to_cm(m.group(1)), to_cm(m.group(2)), to_cm(m.group(3))], reverse=True)
        return (vals[0], vals[1], vals[2])
    return (None, None, None)

def make_skeleton(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

# ===== 判定结构类型 & 生成编码 =====
# 用骨架匹配用户标注的 6 个结构
STRUCT_MAP = {
    '长宽【NxN】cm；高度【Ncm特硬黄】;长宽【NxN】cm;高度【Ncm特硬黄】': ('外径', '特硬'),
    '外径白色高【N厘米】；长x宽【NxN】;外径白色高【N厘米】;长x宽【NxN】': ('外径', '白色'),
    '长NCM': None,  # 定制链接
    'NCM；宽Ncm；高Ncm;NCM;宽Ncm;高Ncm': ('外径', '特硬'),
    'NCM': None,  # 定制链接
    'E瓦;特硬': None,  # 定制链接
}

codes = []  # (店铺名称, 平台商品id, 平台规格id, 商品编码)
custom_cnt = 0
normal_cnt = 0
no_parse = 0

for idx in range(len(shop_data)):
    row = shop_data.iloc[idx]
    shop = str(row['店铺名称'] or '').strip()
    prod_id = str(row['平台商品id'] or '').strip()
    spec = str(row['平台规格名称'] or '').strip()
    spec_id = str(row['平台规格id'] or '').strip()
    
    sk = make_skeleton(spec)
    type_info = STRUCT_MAP.get(sk)
    
    if type_info is None:
        # 定制链接
        codes.append((shop, prod_id, spec_id, '定制链接'))
        custom_cnt += 1
        continue
    
    dim_kind, material = type_info
    l, w, h = extract_lwh(spec)
    
    if l is None or w is None or h is None:
        # 无法解析尺寸，也放定制链接
        codes.append((shop, prod_id, spec_id, '定制链接'))
        no_parse += 1
        continue
    
    # 尺寸转整数（去掉小数点）
    l_int = int(round(l))
    w_int = int(round(w))
    h_int = int(round(h))
    
    # 商品编码格式: L*W*H-内外径-材料
    km_code = f'{l_int}*{w_int}*{h_int}-{dim_kind}-{material}'
    codes.append((shop, prod_id, spec_id, km_code))
    normal_cnt += 1

print(f'已匹配编码: {normal_cnt}, 定制链接: {custom_cnt}, 未解析: {no_parse}')

# ===== 写入 Excel =====
outpath = r'D:\Desktop\换绑_东莞市新鑫星包装材料有限公司.xlsx'
wb = oxl.Workbook()
ws = wb.active
ws.title = 'Sheet1'

# 第1行：商品对应表
ws.append([None, '商品对应表', None, None])
# 第2行：列头
ws.append(['店铺名称', '平台商品id', '平台规格id', '商品编码'])
# 数据
for row_data in codes:
    ws.append(list(row_data))

# 列宽
ws.column_dimensions['A'].width = 30
ws.column_dimensions['B'].width = 18
ws.column_dimensions['C'].width = 18
ws.column_dimensions['D'].width = 25

wb.save(outpath)
wb.close()
print(f'✅ 已生成: {outpath}')
print(f'   共 {len(codes)} 条（正常编码: {normal_cnt}, 定制链接: {custom_cnt}）')
