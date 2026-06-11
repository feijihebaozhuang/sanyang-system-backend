# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'

# ============ 通用工具 ============
def make_skel(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

def extract_num(text):
    """提取文本中第一个数值，支持 2 .5、2.5、2 等各种写法"""
    m = re.search(r'(\d+)\s*\.\s*(\d+)', text)
    if m: return float(m.group(1) + '.' + m.group(2))
    m = re.search(r'(\d+)', text)
    if m: return float(m.group(1))
    return None

def num(s):
    """纯数字串转float"""
    s = s.strip().replace(' ', '')
    return float(s)

# ============ 小批量 ============
def do_xiaopi():
    shop_name = '飞机盒小批量专卖店'
    print(f'\n===== {shop_name} =====')
    df = pd.read_excel(source, dtype=str)
    data = df.iloc[1:].copy()
    data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
    sd = data[data['店铺名称'].str.strip() == shop_name].copy()
    print(f'{shop_name}: {len(sd)} 条')

    # 结构定义: skel -> (dim_kind, material, parser)
    # parser 接收 spec 返回 (l, w, h) 或 None
    CONFIG = {}

    # [1] 宽N高Ncm;长度Ncm【N个】白色  → 外径-白色
    CONFIG['宽N高Ncm;长度Ncm【N个】白色'] = ('外径', '白色',
        lambda s: (extract_num(s.split('长度')[1].split('cm')[0]),
                   extract_num(s.split('宽')[1].split('高')[0]),
                   extract_num(s.split('高')[1].split('cm')[0])))

    # [2] 宽N高Ncm;长度Ncm【N个】超硬黄色  → 外径-超硬
    CONFIG['宽N高Ncm;长度Ncm【N个】超硬黄色'] = ('外径', '超硬',
        lambda s: (extract_num(s.split('长度')[1].split('cm')[0]),
                   extract_num(s.split('宽')[1].split('高')[0]),
                   extract_num(s.split('高')[1].split('cm')[0])))

    # [3] 宽【Ncm】高【Ncm】;【N个】长度【Ncm】  → 外径-特硬
    CONFIG['宽【Ncm】高【Ncm】;【N个】长度【Ncm】'] = ('外径', '特硬',
        lambda s: (extract_num(s.split('长度【')[1]),
                   extract_num(s.split('宽【')[1]),
                   extract_num(s.split('高【')[1])))

    # [4] 宽【Ncm】高【Ncm】白色;【N个】长度【Ncm】  → 外径-白色
    CONFIG['宽【Ncm】高【Ncm】白色;【N个】长度【Ncm】'] = ('外径', '白色',
        lambda s: (extract_num(s.split('长度【')[1]),
                   extract_num(s.split('宽【')[1]),
                   extract_num(s.split('高【')[1])))

    # [5] 宽【Ncm】高【Ncm】白色;【N个】长度【Ncm】【内径】  → 内径-白色
    CONFIG['宽【Ncm】高【Ncm】白色;【N个】长度【Ncm】【内径】'] = ('内径', '白色',
        lambda s: (extract_num(s.split('长度【')[1]),
                   extract_num(s.split('宽【')[1]),
                   extract_num(s.split('高【')[1])))

    # [6] 宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】  → 内径-特硬
    CONFIG['宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】'] = ('内径', '特硬',
        lambda s: (extract_num(s.split('长度【')[1]),
                   extract_num(s.split('宽【')[1]),
                   extract_num(s.split('高【')[1])))

    # [7] 宽N高NCM;长度NCM【N个】超硬黄色  → 外径-超硬
    CONFIG['宽N高NCM;长度NCM【N个】超硬黄色'] = ('外径', '超硬',
        lambda s: (extract_num(s.split('长度')[1]),
                   extract_num(s.split('宽')[1].split('高')[0]),
                   extract_num(s.split('高')[1].split('CM')[0])))

    # [8] 黄色优质特硬【N个】挑战性价比;N×N×N  → 外径-特硬 (mm转cm)
    CONFIG['黄色优质特硬【N个】挑战性价比;N×N×N'] = ('外径', '特硬',
        lambda s: _parse_3nums_mm(s.split(';')[1].strip() if ';' in s else s))

    # [9] 高档超硬【双面白】N个;N×N×N  → 外径-白色
    CONFIG['高档超硬【双面白】N个;N×N×N'] = ('外径', '白色',
        lambda s: _parse_3nums_mm(s.split(';')[1].strip() if ';' in s else s))

    # [10] 双面纯色【N个】黑&红;N×N×N  → 定制
    CONFIG['双面纯色【N个】黑&红;N×N×N'] = ('定制', None, None)

    # [11] 黄色优质特硬【N个】挑战性价比;N×N×Nmm  → 外径-特硬
    CONFIG['黄色优质特硬【N个】挑战性价比;N×N×Nmm'] = ('外径', '特硬',
        lambda s: _parse_3nums_mm(s.split(';')[1].strip() if ';' in s else s))

    # [12] 高档超硬【双面白】N个;N×N×Nmm  → 外径-白色
    CONFIG['高档超硬【双面白】N个;N×N×Nmm'] = ('外径', '白色',
        lambda s: _parse_3nums_mm(s.split(';')[1].strip() if ';' in s else s))

    # [13] 双面纯色【N个】黑&红;N×N×Nmm  → 定制
    CONFIG['双面纯色【N个】黑&红;N×N×Nmm'] = ('定制', None, None)

    # [14] 宽【Ncm】高【Ncm】【内径】;【N个】长度【Nm】【内径】  → 内径-特硬 (长度单位m=cm)
    CONFIG['宽【Ncm】高【Ncm】【内径】;【N个】长度【Nm】【内径】'] = ('内径', '特硬',
        lambda s: (extract_num(s.split('长度【')[1]),
                   extract_num(s.split('宽【')[1]),
                   extract_num(s.split('高【')[1])))

    # [15] 宽【Ncm】高【Ncm】内径;【N个】长【Nm】  → 内径-特硬
    CONFIG['宽【Ncm】高【Ncm】内径;【N个】长【Nm】'] = ('内径', '特硬',
        lambda s: (extract_num(s.split('长【')[1]),
                   extract_num(s.split('宽【')[1]),
                   extract_num(s.split('高【')[1])))

    # [16] 【外尺寸正方形】...  → 定制
    CONFIG['【外尺寸正方形】【内外尺寸长方形飞机盒】【其他链接】;长宽NxNcm内尺寸'] = ('定制', None, None)

    # [17] 黄色-高度N高度cm内径【N个】;长宽NxNcm内尺寸  → 内径-特硬
    CONFIG['黄色-高度N高度cm内径【N个】;长宽NxNcm内尺寸'] = ('内径', '特硬',
        lambda s: _parse_lw_h(s))

    # [18] 宽【Nm】高【Ncm】白色;【N个】长度【Ncm】  → 外径-白色
    CONFIG['宽【Nm】高【Ncm】白色;【N个】长度【Ncm】'] = ('外径', '白色',
        lambda s: (num(s.split('长度【')[1].split('cm')[0]),
                   num(s.split('宽【')[1].split('m')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [19] 宽【Ncm】高【Ncm】白色;【N个】长度【Nm】【内径】  → 内径-白色
    CONFIG['宽【Ncm】高【Ncm】白色;【N个】长度【Nm】【内径】'] = ('内径', '白色',
        lambda s: (num(s.split('长度【')[1].split('m')[0]),
                   num(s.split('宽【')[1].split('cm')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [20] 宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】  → 内径-特硬
    CONFIG['宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】'] = ('内径', '特硬',
        lambda s: (num(s.split('长度【')[1].split('cm')[0]),
                   num(s.split('宽【')[1].split('cm')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [21] 宽【Ncm】高【Ncm】白色;【N个】长度【Nm】  → 外径-白色
    CONFIG['宽【Ncm】高【Ncm】白色;【N个】长度【Nm】'] = ('外径', '白色',
        lambda s: (num(s.split('长度【')[1].split('m')[0]),
                   num(s.split('宽【')[1].split('cm')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [22] 宽【Nm】高【Ncm】;【N个】长【Ncm】  → 外径-特硬
    CONFIG['宽【Nm】高【Ncm】;【N个】长【Ncm】'] = ('外径', '特硬',
        lambda s: (num(s.split('长【')[1].split('cm')[0]),
                   num(s.split('宽【')[1].split('m')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [23] 宽【Ncm】高【Ncm【内径】;【N个】长度【Ncm】【内径】  → 内径-特硬
    CONFIG['宽【Ncm】高【Ncm【内径】;【N个】长度【Ncm】【内径】'] = ('内径', '特硬',
        lambda s: (num(s.split('长度【')[1].split('cm')[0]),
                   num(s.split('宽【')[1].split('cm')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [24] 宽【Ncm】高【Ncm】;【N个】长度【Nm】  → 外径-特硬
    CONFIG['宽【Ncm】高【Ncm】;【N个】长度【Nm】'] = ('外径', '特硬',
        lambda s: (num(s.split('长度【')[1].split('m')[0]),
                   num(s.split('宽【')[1].split('cm')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [25] 宽【Nm】高【Ncm】;【N个】长度【Ncm】  → 外径-特硬
    CONFIG['宽【Nm】高【Ncm】;【N个】长度【Ncm】'] = ('外径', '特硬',
        lambda s: (num(s.split('长度【')[1].split('cm')[0]),
                   num(s.split('宽【')[1].split('m')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [26] 宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】径】  → 内径-特硬
    CONFIG['宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】径】'] = ('内径', '特硬',
        lambda s: (num(s.split('长度【')[1].split('cm')[0]),
                   num(s.split('宽【')[1].split('cm')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [27] 宽【Ncm】高【Ncm】白色个;【N个】长度【Ncm】  → 外径-白色
    CONFIG['宽【Ncm】高【Ncm】白色个;【N个】长度【Ncm】'] = ('外径', '白色',
        lambda s: (num(s.split('长度【')[1].split('cm')[0]),
                   num(s.split('宽【')[1].split('cm')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [28] 宽【Nm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】  → 内径-特硬
    CONFIG['宽【Nm】高【Ncm】【内径】;【N个】长度【Ncm】【内径】'] = ('内径', '特硬',
        lambda s: (num(s.split('长度【')[1].split('cm')[0]),
                   num(s.split('宽【')[1].split('m')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [29] 宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm【内径】】  → 内径-特硬
    CONFIG['宽【Ncm】高【Ncm】【内径】;【N个】长度【Ncm【内径】】'] = ('内径', '特硬',
        lambda s: (num(s.split('长度【')[1].split('cm')[0]),
                   num(s.split('宽【')[1].split('cm')[0]),
                   num(s.split('高【')[1].split('cm')[0])))

    # [30] 优质进口纸-黄色【N个】;N*N**N  → 外径-特硬
    CONFIG['优质进口纸-黄色【N个】;N*N**N'] = ('外径', '特硬',
        lambda s: _parse_star3(s.split(';')[1].strip() if ';' in s else s))

    # [31] 双白色【N个】;N*N**N  → 外径-白色
    CONFIG['双白色【N个】;N*N**N'] = ('外径', '白色',
        lambda s: _parse_star3(s.split(';')[1].strip() if ';' in s else s))

    # [32] 双面纯色【N个】黑&红;N*N**N  → 定制
    CONFIG['双面纯色【N个】黑&红;N*N**N'] = ('定制', None, None)

    # [33] 优质进口纸-黄色【N个】;N*N*N  → 外径-特硬
    CONFIG['优质进口纸-黄色【N个】;N*N*N'] = ('外径', '特硬',
        lambda s: _parse_star3(s.split(';')[1].strip() if ';' in s else s))

    # [34] 双白色【N个】;N*N*N  → 外径-白色
    CONFIG['双白色【N个】;N*N*N'] = ('外径', '白色',
        lambda s: _parse_star3(s.split(';')[1].strip() if ';' in s else s))

    # [35] 双面纯色【N个】黑&红;N*N*N  → 定制
    CONFIG['双面纯色【N个】黑&红;N*N*N'] = ('定制', None, None)

    # [36] 优质进口纸-黄色N个;N*N  → 外径-特硬
    CONFIG['优质进口纸-黄色N个;N*N'] = ('外径', '特硬',
        lambda s: _parse_star2(s.split(';')[1].strip() if ';' in s else s))

    # [37] 双白色N个;N*N  → 外径-白色
    CONFIG['双白色N个;N*N'] = ('外径', '白色',
        lambda s: _parse_star2(s.split(';')[1].strip() if ';' in s else s))

    # [38] 双面纯色【N个】黑&红;N*N  → 定制
    CONFIG['双面纯色【N个】黑&红;N*N'] = ('定制', None, None)

    # [39] 优质进口纸-黄色【N个】;N**N*Ncm  → 外径-特硬
    CONFIG['优质进口纸-黄色【N个】;N**N*Ncm'] = ('外径', '特硬',
        lambda s: _parse_star3(s.split(';')[1].strip().replace('cm','') if ';' in s else s))

    # [40] 双白色【N个】;N**N*Ncm  → 外径-白色
    CONFIG['双白色【N个】;N**N*Ncm'] = ('外径', '白色',
        lambda s: _parse_star3(s.split(';')[1].strip().replace('cm','') if ';' in s else s))

    # [41] 双面纯色【N个】黑&红;N**N*Ncm  → 定制
    CONFIG['双面纯色【N个】黑&红;N**N*Ncm'] = ('定制', None, None)

    # [42-47] 各种定制
    for sk in ['双面黑色【N个】;超【大】飞机盒N-N厘米长度',
               '双面黑色【N个】;超【小】飞机盒单位CM厘米',
               '浅黄色【特硬N个】;超【大】飞机盒N-N厘米长度',
               '浅黄色【特硬N个】;超【小】飞机盒单位CM厘米',
               '高档【双面白色N个】;超【大】飞机盒N-N厘米长度',
               '高档【双面白色N个】;超【小】飞机盒单位CM厘米']:
        CONFIG[sk] = ('定制', None, None)

    codes = []
    n_ok = n_cus = n_fail = 0
    for idx in range(len(sd)):
        row = sd.iloc[idx]
        shop = str(row['店铺名称'] or '').strip()
        pid = str(row['平台商品id'] or '').strip()
        spec = str(row['平台规格名称'] or '').strip()
        sid = str(row['平台规格id'] or '').strip()
        sk = make_skel(spec)
        cfg = CONFIG.get(sk)
        if cfg is None:
            codes.append((shop, pid, sid, '定制链接')); n_cus += 1; continue
        dk, mat, fn = cfg
        if dk == '定制':
            codes.append((shop, pid, sid, '定制链接')); n_cus += 1; continue
        try:
            dims = fn(spec)
            if dims is None or any(v is None for v in dims):
                codes.append((shop, pid, sid, '定制链接')); n_fail += 1; continue
            l, w, h = dims
            li = max(1, int(round(l)))
            wi = max(1, int(round(w)))
            hi = max(1, int(round(h)))
            codes.append((shop, pid, sid, f'{li}*{wi}*{hi}-{dk}-{mat}'))
            n_ok += 1
        except:
            codes.append((shop, pid, sid, '定制链接')); n_fail += 1

    print(f'  正常: {n_ok}, 定制: {n_cus}, 失败: {n_fail}')
    _write_excel(r'D:\Desktop\换绑_飞机盒小批量专卖店.xlsx', codes)
    print(f'  ✅ 换绑_飞机盒小批量专卖店.xlsx')


# ============ 三羊 ============
def do_sanyang():
    shop_name = '深圳市三羊包装材料有限公司'
    print(f'\n===== {shop_name} =====')
    df = pd.read_excel(source, dtype=str)
    data = df.iloc[1:].copy()
    data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
    sd = data[data['店铺名称'].str.strip() == shop_name].copy()
    print(f'{shop_name}: {len(sd)} 条')

    CONFIG = {}

    # [1] 长*宽【N*N】cm；外尺寸N级特硬原色；【Ncm高】 → 外径-特硬
    CONFIG['长*宽【N*N】cm；外尺寸N级特硬原色；【Ncm高】;长*宽【N*N】cm;外尺寸N级特硬原色;【Ncm高】'] = ('外径', '特硬',
        lambda s: _parse_sanyang_lw_cm(s))

    # [2] 外尺寸特硬双面白 → 外径-白色
    CONFIG['长*宽【N*N】；外尺寸特硬双面白；【Ncm高】;长*宽【N*N】;外尺寸特硬双面白;【Ncm高】'] = ('外径', '白色',
        lambda s: _parse_sanyang_lw(s))

    # [3] 外尺寸特硬原色 → 内径-特硬 (用户标注 "内")
    CONFIG['长*宽【N*N】；外尺寸特硬原色；【Ncm高】;长*宽【N*N】;外尺寸特硬原色;【Ncm高】'] = ('内径', '特硬',
        lambda s: _parse_sanyang_lw(s))

    # [4] 长*宽【N*N】cm;外尺寸白色【Ncm高】 → 内径-白色
    CONFIG['长*宽【N*N】cm;外尺寸白色【Ncm高】'] = ('内径', '白色',
        lambda s: _parse_sanyang_lw_cm_tail(s))

    # [5] 外尺寸N级特硬原色 → 内径-特硬
    CONFIG['长*宽【N*N】；外尺寸N级特硬原色；【Ncm高】;长*宽【N*N】;外尺寸N级特硬原色;【Ncm高】'] = ('内径', '特硬',
        lambda s: _parse_sanyang_lw(s))

    # [6] 外尺寸特硬双面白色 → 外径-白色
    CONFIG['长*宽【N*N】；外尺寸特硬双面白色；【Ncm高】;长*宽【N*N】;外尺寸特硬双面白色;【Ncm高】'] = ('外径', '白色',
        lambda s: _parse_sanyang_lw(s))

    # [7] 长*宽【N*N】cm；外尺寸特硬双面白色 → 外径-白色
    CONFIG['长*宽【N*N】cm；外尺寸特硬双面白色；【Ncm高】;长*宽【N*N】cm;外尺寸特硬双面白色;【Ncm高】'] = ('外径', '白色',
        lambda s: _parse_sanyang_lw_cm(s))

    # [8] 特硬牛皮色【长*宽】N*N;【高】NcmN个一组 → 外径-特硬
    CONFIG['特硬牛皮色【长*宽】N*N;【高】NcmN个一组'] = ('外径', '特硬',
        lambda s: (extract_num(s.split('【长*宽】')[1].split('*')[0]),
                   extract_num(s.split('*')[1].split(';')[0]),
                   extract_num(s.split('【高】')[1])))

    # [9] 宽高N*N（牛皮色）;长NcmSN级硬度 → 外径-特硬
    CONFIG['宽高N*N（牛皮色）;长NcmSN级硬度'] = ('外径', '特硬',
        lambda s: (extract_num(s.split('长')[1]),
                   extract_num(s.split('宽高')[1].split('*')[0]),
                   extract_num(s.split('*')[1].split('（')[0].split(')')[0])))
    # Actually N*N -> w*h, so l is from 长, w from first N, h from second N
    # Let me redo: "宽高10*10（牛皮色）;长10cmS5级硬度"
    # width=10, height=10, length=10

    # [10] 宽高N*N（白色）;长NcmSN级硬度 → 外径-白色
    CONFIG['宽高N*N（白色）;长NcmSN级硬度'] = ('外径', '白色',
        lambda s: (extract_num(s.split('长')[1]),
                   extract_num(s.split('宽高')[1].split('*')[0]),
                   extract_num(s.split('*')[1].split('（')[0].split(')')[0])))

    # 用通用解析器处理剩下的
    for skel, (dk, mat) in {
        '长*宽【N*N】；外尺寸N级特硬双面白；Ncm高;长*宽【N*N】;外尺寸N级特硬双面白;Ncm高': ('外径', '白色'),
        '长*宽【N*N】；内寸N级特硬双面白；Ncm高;长*宽【N*N】;内寸N级特硬双面白;Ncm高': ('内径', '白色'),
        '长*宽【N*N】；内寸N级特硬原色；Ncm高;长*宽【N*N】;内寸N级特硬原色;Ncm高': ('内径', '特硬'),
        '长*宽【N*N】；外尺寸N级特硬原色；Ncm高;长*宽【N*N】;外尺寸N级特硬原色;Ncm高': ('外径', '特硬'),
        '长*宽【N*N】；外尺寸N级特硬双面白；【Ncm高】;长*宽【N*N】;外尺寸N级特硬双面白;【Ncm高】': ('外径', '白色'),
        '长*宽【N*N】；外尺寸N级超硬原色；【Ncm高】;长*宽【N*N】;外尺寸N级超硬原色;【Ncm高】': ('外径', '超硬'),
        '长*宽【N*N】；内寸N级特硬原色；【Ncm高】;长*宽【N*N】;内寸N级特硬原色;【Ncm高】': ('内径', '特硬'),
        '长*宽【N*N】；内寸N级超硬原色；【Ncm高】;长*宽【N*N】;内寸N级超硬原色;【Ncm高】': ('内径', '超硬'),
        '长*宽【N*N】cm；外尺寸【双面黑】；【Ncm高】;长*宽【N*N】cm;外尺寸【双面黑】;【Ncm高】': ('外径', '黑色'),
        '长*宽【N*N】；外尺寸N级特硬原色；【N高】;长*宽【N*N】;外尺寸N级特硬原色;【N高】': ('内径', '特硬'),
        '长*宽【N*N】cm；外尺寸N级特硬原色；【【Ncm高】;长*宽【N*N】cm;外尺寸N级特硬原色;【【Ncm高】': ('外径', '特硬'),
        '长*宽【N*N】cm；外尺寸N级特硬原色；【外尺寸】【Ncm高】特硬牛皮色;长*宽【N*N】cm;外尺寸N级特硬原色;【外尺寸】【Ncm高】特硬牛皮色': ('外径', '特硬'),
        '长*宽【N*Ncm；外尺寸N级特硬原色；【Ncm高】;长*宽【N*Ncm;外尺寸N级特硬原色;【Ncm高】': ('外径', '特硬'),
        '长*宽【N*N】c；外尺寸特硬原色；【Ncm高】;长*宽【N*N】c;外尺寸特硬原色;【Ncm高】': ('内径', '特硬'),
    }.items():
        CONFIG[skel] = (dk, mat, lambda s, _skel=skel: _generic_sanyang(s, _skel))

    # red/black ones
    CONFIG['外尺寸【长*宽】N*N;【高】Ncm红色'] = ('定制', None, None)
    CONFIG['外尺寸【长*宽】N*N;【高】Ncm黑色'] = ('外径', '黑色', lambda s: (
        extract_num(s.split('【高】')[1]),
        extract_num(s.split('【长*宽】')[1].split('*')[0]),
        extract_num(s.split('*')[1].split(';')[0])))

    CONFIG['长*宽【N*N】cm；外尺寸【双面红】；【Ncm高】;长*宽【N*N】cm;外尺寸【双面红】;【Ncm高】'] = ('定制', None, None)
    CONFIG['特硬;飞机盒'] = ('定制', None, None)

    codes = []
    n_ok = n_cus = n_fail = 0
    for idx in range(len(sd)):
        row = sd.iloc[idx]
        shop = str(row['店铺名称'] or '').strip()
        pid = str(row['平台商品id'] or '').strip()
        spec = str(row['平台规格名称'] or '').strip()
        sid = str(row['平台规格id'] or '').strip()
        sk = make_skel(spec)
        cfg = CONFIG.get(sk)
        if cfg is None:
            codes.append((shop, pid, sid, '定制链接')); n_cus += 1; continue
        dk, mat, fn = cfg
        if dk == '定制':
            codes.append((shop, pid, sid, '定制链接')); n_cus += 1; continue
        try:
            dims = fn(spec)
            if dims is None or any(v is None for v in dims):
                codes.append((shop, pid, sid, '定制链接')); n_fail += 1; continue
            l, w, h = dims
            li = max(1, int(round(l)))
            wi = max(1, int(round(w)))
            hi = max(1, int(round(h)))
            codes.append((shop, pid, sid, f'{li}*{wi}*{hi}-{dk}-{mat}'))
            n_ok += 1
        except:
            codes.append((shop, pid, sid, '定制链接')); n_fail += 1

    print(f'  正常: {n_ok}, 定制: {n_cus}, 失败: {n_fail}')
    _write_excel(r'D:\Desktop\换绑_深圳市三羊包装材料有限公司.xlsx', codes)
    print(f'  ✅ 换绑_深圳市三羊包装材料有限公司.xlsx')


# ============ 通用辅助函数 ============
def _parse_3nums_mm(s):
    """解析 N×N×N 或 N×N×Nmm，>100的mm转cm"""
    nums = re.findall(r'(\d+\.?\d*)', s.replace('×','*').replace('x','*').replace('X','*'))
    if len(nums) < 3: return None
    vals = sorted([float(nums[0]), float(nums[1]), float(nums[2])], reverse=True)
    if 'mm' in s and vals[0] >= 100:
        vals = [v/10 for v in vals]
    return (vals[0], vals[1], vals[2])

def _parse_star3(s):
    """解析 N*N**N 或 N*N*N"""
    nums = []
    for ch in re.split(r'\*+', s):
        ch = ch.strip().replace('cm','')
        if ch and re.match(r'[\d.]+$', ch):
            nums.append(float(ch))
    if len(nums) < 3: return None
    vals = sorted(nums, reverse=True)
    return (vals[0], vals[1], vals[2])

def _parse_star2(s):
    """解析 N*N，没有高时用宽代替"""
    nums = re.findall(r'(\d+\.?\d*)', s.replace('*','x'))
    if len(nums) < 2: return None
    l, w = float(nums[0]), float(nums[1])
    return (l, w, w)

def _parse_lw_h(s):
    """长宽NxNcm + 高度Ncm"""
    l = extract_num(s.split('长宽度')[1] if '长宽度' in s else s.split('长宽')[1]) if '长宽' in s else None
    w = extract_num(s.split('x')[1]) if 'x' in s else None
    h = extract_num(s.split('高度')[1]) if '高度' in s else None
    return (l, w, h)

def _parse_sanyang_lw_cm(s):
    """长*宽【N*N】cm；...【Ncm高】"""
    s2 = re.sub(r'(\d+)\s+\.\s*(\d+)', r'\1.\2', s)
    s2 = re.sub(r'(\d+)\s*\.\s+(\d+)', r'\1.\2', s2)
    m = re.search(r'【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】cm', s2)
    if not m: return None
    l, w = float(m.group(1).replace(' ','')), float(m.group(2).replace(' ',''))
    m = re.search(r'【\s*([\d.]+)\s*\.?\s*(\d*)\s*cm\s*高】', s2)
    if not m: return None
    h = float(m.group(1).replace(' ','') + ('.' + m.group(2).replace(' ','') if m.group(2) else ''))
    return (l, w, h)

def _parse_sanyang_lw(s):
    """长*宽【N*N】（无cm）；...【Ncm高】"""
    s2 = re.sub(r'(\d+)\s+\.\s*(\d+)', r'\1.\2', s)
    s2 = re.sub(r'(\d+)\s*\.\s+(\d+)', r'\1.\2', s2)
    m = re.search(r'【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】', s2)
    if not m: return None
    l, w = float(m.group(1).replace(' ','')), float(m.group(2).replace(' ',''))
    m = re.search(r'【\s*([\d.]+)\s*\.?\s*(\d*)\s*cm\s*高】', s2)
    if not m:
        m = re.search(r'([\d.]+)\s*\.?\s*(\d*)\s*cm\s*高', s2)
    if not m:
        m = re.search(r'【\s*([\d.]+)\s*高】', s2)
    if not m: return None
    h = float(m.group(1).replace(' ','') + ('.' + m.group(2).replace(' ','') if len(m.groups())>=2 and m.group(2) else ''))
    return (l, w, h)

def _parse_sanyang_lw_cm_tail(s):
    """长*宽【N*N】cm;外尺寸白色【Ncm高】"""
    # 先标准化数字中的空格: "12 .5" -> "12.5"
    s2 = re.sub(r'(\d+)\s+\.\s*(\d+)', r'\1.\2', s)
    s2 = re.sub(r'(\d+)\s*\.\s+(\d+)', r'\1.\2', s2)
    m = re.search(r'【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】cm', s2)
    if not m: return None
    l, w = float(m.group(1).replace(' ','')), float(m.group(2).replace(' ',''))
    # 处理 【2 .5cm高】 这种空格隔开小数点的情况
    m = re.search(r'【\s*(\d+)\s*\.\s*(\d+)\s*cm\s*高】', s2)
    if m: h = float(m.group(1) + '.' + m.group(2))
    else:
        m = re.search(r'【\s*([\d.]+)\s*cm\s*高】', s2)
        if m: h = float(m.group(1).replace(' ',''))
        else: return None
    return (l, w, h)

def _generic_sanyang(s, skel):
    """通用三羊解析器：提取【N*N】和 cm高"""
    s2 = re.sub(r'(\d+)\s+\.\s*(\d+)', r'\1.\2', s)
    s2 = re.sub(r'(\d+)\s*\.\s+(\d+)', r'\1.\2', s2)
    # 处理 【N*Ncm 缺少】的情况
    m = re.search(r'【\s*([\d.]+)\s*\*\s*([\d.]+)\s*(?:】\s*)?cm', s2)
    if not m:
        m = re.search(r'【\s*([\d.]+)\s*\*\s*([\d.]+)\s*】', s2)
    if not m: return None
    l = float(m.group(1).replace(' ',''))
    w = float(m.group(2).replace(' ',''))
    # 尝试各种cm高
    m = re.search(r'【\s*(\d+)\s*\.\s*(\d+)\s*cm\s*高】', s2)
    if m: h = float(m.group(1) + '.' + m.group(2))
    else:
        m = re.search(r'【【?\s*([\d.]+)\s*cm\s*高】?', s2)
        if m: h = float(m.group(1).replace(' ',''))
        else:
            m = re.search(r'([\d.]+)\s*\.?\s*(\d*)\s*cm\s*高', s2)
            if m:
                num_part = m.group(1).replace(' ','')
                dec_part = m.group(2).replace(' ','') if len(m.groups())>=2 and m.group(2) else ''
                h = float(num_part + ('.' + dec_part if dec_part else ''))
            else:
                # 尝试纯【N高】无cm
                m = re.search(r'【\s*([\d.]+)\s*高】', s2)
                if m: h = float(m.group(1).replace(' ',''))
                else: return None
    return (l, w, h)

def _write_excel(path, codes):
    wb = oxl.Workbook()
    ws = wb.active
    ws.title = 'Sheet1'
    ws.append([None, '商品对应表', None, None])
    ws.append(['店铺名称', '平台商品id', '平台规格id', '商品编码'])
    for r in codes:
        ws.append(list(r))
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 25
    wb.save(path)
    wb.close()

# ============ 主程序 ============
do_xiaopi()
do_sanyang()
print('\n✅ 全部完成！')
