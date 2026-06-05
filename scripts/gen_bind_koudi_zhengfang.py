# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'

def make_skel(s):
    return re.sub(r'\d+\.?\d*', 'N', re.sub(r'\s+', '', s))[:300]

def grab_num(text, after=None, before=None):
    """提取 after..before 之间的第一个数值"""
    s = text.replace(' ', '')
    if after:
        i = s.find(after)
        if i < 0: return None
        s = s[i+len(after):]
    if before:
        i = s.find(before)
        if i >= 0: s = s[:i]
    m = re.search(r'(\d+(?:\.\d+)?)', s)
    return float(m.group(1)) if m else None

def grab_two(text, after=None, before=None):
    """提取 after..before 之间的两个数值"""
    s = text.replace(' ', '')
    if after:
        i = s.find(after)
        if i < 0: return None
        s = s[i+len(after):]
    if before:
        i = s.find(before)
        if i >= 0: s = s[:i]
    nums = re.findall(r'(\d+(?:\.\d+)?)', s)
    if len(nums) >= 2: return (float(nums[0]), float(nums[1]))
    return None

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

def process_shop(shop_name, outfile, CONFIG):
    df = pd.read_excel(source, dtype=str)
    data = df.iloc[1:].copy()
    data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
    sd = data[data['店铺名称'].str.strip() == shop_name].copy()
    print(f'{shop_name}: {len(sd)} 条')

    codes = []
    n_ok = n_cus = n_zx = n_fail = 0
    for idx in range(len(sd)):
        row = sd.iloc[idx]
        shop_n = str(row['店铺名称'] or '').strip()
        pid = str(row['平台商品id'] or '').strip()
        spec = str(row['平台规格名称'] or '').strip()
        sid = str(row['平台规格id'] or '').strip()
        sk = make_skel(spec)
        cfg = CONFIG.get(sk)
        if cfg is None:
            codes.append((shop_n, pid, sid, '定制链接')); n_cus += 1; continue
        dk, mat, fn = cfg
        if dk == '定制':
            codes.append((shop_n, pid, sid, '定制链接')); n_cus += 1; continue
        try:
            dims = fn(spec)
            if dims is None or any(v is None for v in dims):
                codes.append((shop_n, pid, sid, '定制链接')); n_fail += 1; continue
            if dk == '纸箱':
                l, w, h = dims
                li, wi, hi = max(1,int(round(l))), max(1,int(round(w))), max(1,int(round(h)))
                codes.append((shop_n, pid, sid, f'{li}*{wi}*{hi}-EB'))
                n_zx += 1
            else:
                l, w, h = dims
                li, wi, hi = max(1,int(round(l))), max(1,int(round(w))), max(1,int(round(h)))
                codes.append((shop_n, pid, sid, f'{li}*{wi}*{hi}-{dk}-{mat}'))
                n_ok += 1
        except:
            codes.append((shop_n, pid, sid, '定制链接')); n_fail += 1
    print(f'  正常: {n_ok}, 纸箱EB: {n_zx}, 定制: {n_cus}, 失败: {n_fail}')
    _write_excel(outfile, codes)
    print(f'  ✅ {outfile}')

# ====================================================================
#                          扣底盒
# ====================================================================
def koudi_1(s):
    """[1] 外宽x高【NxN】=... 外尺寸【长度Ncm】=【内长Ncm】"""
    wh = grab_two(s, after='外宽x高【', before='】=')
    l = grab_num(s, after='外尺寸【长度')
    if not wh or not l: return None
    return (l, wh[0], wh[1])  # l=外尺寸长度, w=宽, h=高

def koudi_10(s):
    """[10] 同[1]但缺最后]"""
    wh = grab_two(s, after='外宽x高【', before='】=')
    if not wh: wh = grab_two(s, after='外宽x高【', before='=')
    l = grab_num(s, after='外尺寸【长度')
    if not wh or not l: return None
    return (l, wh[0], wh[1])

def koudi_2(s):
    """[2] 内宽x高【NxN】=外宽x高...内尺寸【长度Ncm】=【外长Ncm】"""
    wh = grab_two(s, after='内宽x高【', before='】=')
    l = grab_num(s, after='内尺寸【长度')
    if not wh or not l: return None
    return (l, wh[0], wh[1])

def koudi_3(s):
    """[3] 宽度N【白色】;外尺寸【长度Ncm】----高度Ncm"""
    return (grab_num(s, after='外尺寸【长度'), grab_num(s, after='宽度'),
            grab_num(s, after='----高度'))

def koudi_5(s):
    """[5] 宽度N【黑色】;外尺寸【长度Ncm】----高度Ncm"""
    return koudi_3(s)

def koudi_6(s):
    """[6] 宽度N【白色】;【N个外尺寸】长度Ncm----高度Ncm"""
    return (grab_num(s, after='】长度'), grab_num(s, after='宽度'),
            grab_num(s, after='高度'))

def koudi_8(s):
    """[8] 宽度N【黑色】;【N个外尺寸】长度Ncm----高度Ncm"""
    return koudi_6(s)

def koudi_9(s):
    """[9] N*Ncm;Ncm高;五层 → EB"""
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[0]), float(nums[1]), float(nums[2]))

def koudi_11(s):
    """[11] 宽度N【白色】;外尺寸【长度Ncm】----高度Nm"""
    return (grab_num(s, after='外尺寸【长度'), grab_num(s, after='宽度'),
            grab_num(s, after='高度'))

def koudi_12(s):
    """[12] 同[11] 黑色"""
    return koudi_11(s)

def koudi_14(s):
    """[14] 宽度N【白色】;【N个】【外尺寸】长度Ncm----高度Ncm"""
    return (grab_num(s, after='【外尺寸】长度'), grab_num(s, after='宽度'),
            grab_num(s, after='高度'))

def koudi_16(s):
    """[16] 同[14] 黑色"""
    return koudi_14(s)

K_CONFIG = {
    '外宽x高【NxN】=内宽x高【NxN】cm;【N个】外尺寸【长度Ncm】=【内长Ncm】': ('外径', '特硬', koudi_1),
    '内宽x高【NxN】=外宽x高【NxN】cm;【N个】内尺寸【长度Ncm】=【外长Ncm】': ('内径', '特硬', koudi_2),
    '宽度N【白色】;【N个】外尺寸【长度Ncm】----高度Ncm': ('外径', '白色', koudi_3),
    '宽度N【红色】;【N个】外尺寸【长度Ncm】----高度Ncm': ('定制', None, None),
    '宽度N【黑色】;【N个】外尺寸【长度Ncm】----高度Ncm': ('外径', '黑色', koudi_5),
    '宽度N【白色】;【N个外尺寸】长度Ncm----高度Ncm': ('外径', '白色', koudi_6),
    '宽度N【红色】;【N个外尺寸】长度Ncm----高度Ncm': ('定制', None, None),
    '宽度N【黑色】;【N个外尺寸】长度Ncm----高度Ncm': ('外径', '黑色', koudi_8),
    'N*Ncm;Ncm高;五层': ('纸箱', None, koudi_9),
    '外宽x高【NxN】=内宽x高【NxN】cm;【N个】外尺寸【长度Ncm】=【内长Ncm': ('外径', '特硬', koudi_10),
    '宽度N【白色】;【N个】外尺寸【长度Ncm】----高度Nm': ('外径', '白色', koudi_11),
    '宽度N【黑色】;【N个】外尺寸【长度Ncm】----高度Nm': ('外径', '黑色', koudi_12),
    '宽度N【红色】;【N个】外尺寸【长度Ncm】----高度Nm': ('定制', None, None),
    '宽度N【白色】;【N个】【外尺寸】长度Ncm----高度Ncm': ('外径', '白色', koudi_14),
    '宽度N【红色】;【N个】【外尺寸】长度Ncm----高度Ncm': ('定制', None, None),
    '宽度N【黑色】;【N个】【外尺寸】长度Ncm----高度Ncm': ('外径', '黑色', koudi_16),
    '按照价格截图客服拍下;下拉看详情选择尺寸': ('定制', None, None),
}

# ====================================================================
#                        正方形
# ====================================================================
def zf_mm(s):
    """白色内径/外径/黄色内径/黄色外径】高度【Nmm】;【N个】长*宽【N*Nmm】"""
    m = re.search(r'【\s*(\d+(?:\.\d+)?)\s*[\*xX×]\s*(\d+(?:\.\d+)?)\s*mm?】?', s.replace(' ', ''))
    m2 = re.search(r'高度【\s*(\d+(?:\.\d+)?)\s*mm', s.replace(' ', ''))
    if not m or not m2: return None
    return (float(m.group(1))/10, float(m.group(2))/10, float(m2.group(1))/10)

def zf_mm_outside(s):
    """高度【Nmm】X色【内/外径】;【N个】长*宽【N*N】mm"""
    m = re.search(r'【\s*(\d+(?:\.\d+)?)\s*[\*xX×]\s*(\d+(?:\.\d+)?)\s*】\s*mm', s.replace(' ', ''))
    m2 = re.search(r'高度【\s*(\d+(?:\.\d+)?)\s*mm', s.replace(' ', ''))
    if not m or not m2: return None
    return (float(m.group(1))/10, float(m.group(2))/10, float(m2.group(1))/10)

def zf_nkuan_46(s):
    """N宽----------------------------------------------N宽 (46 dashes)"""
    return zf_nkuan(s)

def zf_nkuan_38(s):
    """N宽--------------------------------------N宽 (38 dashes)"""
    return zf_nkuan(s)

def zf_nkuan(s):
    nums = re.findall(r'(\d+)\s*宽', s)
    h = grab_num(s, after='高度【')
    if len(nums) < 2 or not h: return None
    w, l = float(nums[0]), float(nums[1])
    return (l, w, h/10)

# 缺失【的模板：先 normalize 再走 zf_mm
def zf_mm_norm(s):
    s2 = s.replace(' ', '')
    s2 = re.sub(r'长\*宽(\d[\d.*]*)mm】', r'长*宽【\1mm】', s2)
    return zf_mm(s2)

Z_CONFIG = {
    '白色内径】高度【Nmm】;【N个】长*宽【N*Nmm】': ('内径', '白色', zf_mm),
    '高度【Nmm】黄色【内径】;【N个】长*宽【N*Nmm】': ('内径', '特硬', zf_mm),
    '高度【Nmm】黄色【外径】;【N个】长*宽【N*Nmm】': ('外径', '特硬', zf_mm),
    '白色外径】高度【Nmm】;【N个】长*宽【N*Nmm】': ('外径', '白色', zf_mm),

    '白色内径】高度【Nmm】;长*宽【N*Nmm】N个': ('内径', '白色', zf_mm),
    '白色外径】高度【Nmm】;长*宽【N*Nmm】N个': ('外径', '白色', zf_mm),
    '高度【Nmm】黄色【内径】;长*宽【N*Nmm】N个': ('内径', '特硬', zf_mm),
    '高度【Nmm】黄色【外径】;长*宽【N*Nmm】N个': ('外径', '特硬', zf_mm),

    '高度【Nmm】【内径】黄色;【N个】长*宽【N*N】mm': ('内径', '特硬', zf_mm_outside),
    '高度【Nmm】【外径】黄色;【N个】长*宽【N*N】mm': ('外径', '特硬', zf_mm_outside),
    '高度【Nmm】白色【内径】;【N个】长*宽【N*N】mm': ('内径', '白色', zf_mm_outside),
    '高度【Nmm】白色【外径】;【N个】长*宽【N*N】mm': ('外径', '白色', zf_mm_outside),

    '透明白色外径】高度【Nmm】;【N个】长*宽【N*Nmm】': ('外径', '白色', zf_mm),

    '白色内径】高度【Nmm】;【N个】长*宽N*Nmm】': ('内径', '白色', zf_mm_norm),
    '白色外径】高度【Nmm】;【N个】长*宽N*Nmm】': ('外径', '白色', zf_mm_norm),
    '高度【Nmm】黄色【内径】;【N个】长*宽N*Nmm】': ('内径', '特硬', zf_mm_norm),
    '高度【Nmm】黄色【外径】;【N个】长*宽N*Nmm】': ('外径', '特硬', zf_mm_norm),

    '白色内径】高度【Nmm】;N宽----------------------------------------------N宽': ('内径', '白色', zf_nkuan_46),
    '白色外径】高度【Nmm】;N宽----------------------------------------------N宽': ('外径', '白色', zf_nkuan_46),
    '高度【Nmm】黄色【内径】;N宽----------------------------------------------N宽': ('内径', '特硬', zf_nkuan_46),
    '高度【Nmm】黄色【外径】;N宽----------------------------------------------N宽': ('外径', '特硬', zf_nkuan_46),

    '白色内径】高度【Nmm】;N宽--------------------------------------N宽': ('内径', '白色', zf_nkuan_38),
    '白色外径】高度【Nmm】;N宽--------------------------------------N宽': ('外径', '白色', zf_nkuan_38),
    '高度【Nmm】黄色【内径】;N宽--------------------------------------N宽': ('内径', '特硬', zf_nkuan_38),
    '高度【Nmm】黄色【外径】;N宽--------------------------------------N宽': ('外径', '特硬', zf_nkuan_38),
}

# ====================================================================
print('===== 飞机盒扣底盒专卖店 =====')
process_shop('飞机盒扣底盒专卖店', r'D:\Desktop\换绑_飞机盒扣底盒专卖店.xlsx', K_CONFIG)
print()
print('===== 飞机盒正方形专卖店 =====')
process_shop('飞机盒正方形专卖店', r'D:\Desktop\换绑_飞机盒正方形专卖店.xlsx', Z_CONFIG)
print('\n✅ 全部完成！')
