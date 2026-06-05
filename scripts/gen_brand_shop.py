# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '飞机盒品牌店'

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

# ====== 读取数据 ======
print('读取中...')
df = pd.read_excel(source, dtype=str, header=None)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
sd = data[data['店铺名称'].str.strip() == shop_name].copy()
print(f'{shop_name}: {len(sd)} 条')

# ====== 解析器定义 ======
CONFIG = {}

# ===== 第1组: （宽x高）NxNcm;外径【N个】长度Ncm =====
def p1_3(s):
    """（宽x高）NxNcm;外径【N个】长度Ncm  或  ;外径【台湾纸】长度Ncm 或 ;外径【双面白】长度Ncm"""
    wh = grab_two(s, after='（宽x高）')
    if not wh: wh = grab_two(s, after='宽x高）')
    if not wh: return None
    l = grab_num(s, after='长度')
    if not l: return None
    return (l, wh[0], wh[1])

for sk, mat in [
    ('（宽x高）NxNcm;外径【N个】长度Ncm', '特硬'),
    ('（宽x高）NxNcm;外径【台湾纸】长度Ncm', '超硬'),
    ('（宽x高）NxNcm【N个】;外径【双面白】长度Ncm', '白色'),
]:
    CONFIG[sk] = ('外径', mat, p1_3)

# ===== 第2组: 【宽】Ncm...;外径...长度Ncm;【高】Ncm =====
def p4_6(s):
    """【宽】Ncm【N个】;外径【双面白】长度Ncm;【高】Ncm 等"""
    l = grab_num(s, after='长度')
    w = grab_num(s, after='【宽】')
    h = grab_num(s, after='【高】')
    if not l or not w or not h: return None
    return (l, w, h)

for sk, mat in [
    ('【宽】Ncm【N个】;外径【双面白】长度Ncm;【高】Ncm', '白色'),
    ('【宽】Ncm;外径【N个】长度Ncm;【高】Ncm', '特硬'),
    ('【宽】Ncm;外径【单个价】长度Ncm;【高】Ncm台湾纸', '超硬'),
]:
    CONFIG[sk] = ('外径', mat, p4_6)

# ===== 第3组: 宽x高）NxNcm外径;长度Ncm【N个】 =====
def p7_8(s):
    """宽x高）NxNcm外径;长度Ncm【N个】  -> 用户标了内径"""
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    wh = grab_two(s, after='宽x高）')
    if not wh: wh = grab_two(s, after='x高）')
    if wh:
        h = wh[1]
        l = grab_num(s, after='长度')
        if not l:
            l = float(nums[0])
        return (l, wh[0], h)
    return None

CONFIG['宽x高）NxNcm外径;长度Ncm【N个】'] = ('内径', '特硬', p7_8)

def p8_fix(s):
    """宽x高）NxNcm;【外径-N个】长度Ncm -> 内径-特硬"""
    wh = grab_two(s, after='宽x高）')
    l = grab_num(s, after='长度')
    if not wh or not l:
        nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
        if len(nums) >= 3:
            return (float(nums[2]) if len(nums)>2 else 0, float(nums[0]), float(nums[1]))
        return None
    return (l, wh[0], wh[1])

CONFIG['宽x高）NxNcm;【外径-N个】长度Ncm'] = ('内径', '特硬', p8_fix)

# ===== 第4组: 宽度【Nmm】;长度【Nmm】外径... =====
def p9(s):
    """宽度【Nmm】;长度【Nmm】外径【N个】;【Nmm】"""
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[1])/10, float(nums[0])/10, float(nums[2])/10)

CONFIG['宽度【Nmm】;长度【Nmm】外径【N个】;【Nmm】'] = ('外径', '特硬', p9)

def p10(s):
    """宽度【Ncm】;长度【Ncm】;高度【Ncm】N个"""
    return (grab_num(s, after='长度【'), grab_num(s, after='宽度【'), grab_num(s, after='高度【'))

CONFIG['宽度【Ncm】;长度【Ncm】;高度【Ncm】N个'] = ('外径', '特硬', p10)

# ===== 第5组: mm尺寸 台湾纸/双面白 系列 =====
def p11_14(s):
    """mm系列：提取3个数值/10转cm"""
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    vals = [float(n)/10 for n in nums[:3]]
    return (vals[0], vals[1], vals[2])

for sk, (dk, mat) in [
    ('宽度【Nmm】;长度【Nmm】台湾纸;高度【Nmm】单个价', ('内径', '超硬')),
    ('长度Nmm;（宽）Nmm外径台湾纸;【高】Nmm外径', ('内径', '超硬')),
    ('（宽）Nmm外径;【N个】长度Nmm;Nmm双面白', ('内径', '白色')),
    ('长度Nmm;（宽）Nmm外径单个价;【高】Nmm外径', ('内径', '特硬')),
]:
    CONFIG[sk] = (dk, mat, p11_14)

# ===== 第6组: 【宽】Ncm台湾纸...等 =====
def p15(s):
    l = grab_num(s, after='长度')
    w = grab_num(s, after='【宽】')
    h = grab_num(s, after='高【')
    if not l or not w or not h: return None
    return (l, w, h)

CONFIG['【宽】Ncm台湾纸;外径【单个价】长度Ncm;高【Ncm】'] = ('外径', '超硬', p15)

def p16_26(s):
    """宽x高）NxNcm 系列 -> 内径"""
    wh = grab_two(s, after='宽x高）')
    if not wh: wh = grab_two(s, after='x高）')
    if not wh: wh = grab_two(s, after='宽高）')
    if not wh: wh = grab_two(s, after='（宽高）')
    if not wh:
        nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
        if len(nums) >= 3: return (float(nums[2]) if len(nums)>2 else 0, float(nums[0]), float(nums[1]))
        return None
    l = None
    for kw in ['长度', '长']:
        l = grab_num(s, after=kw)
        if l: break
    if not l:
        return None
    return (l, wh[0], wh[1])

for sk, (dk, mat) in [
    ('宽x高）NxNcm外径双面白;【N个】长度Ncm', ('内径', '白色')),
    ('（宽高）NxNcm【N个】;外径【双面白】长度Ncm', ('外径', '白色')),
    ('（宽x高）NxNcm外径双面白;【N个】长度Ncm', ('内径', '白色')),
    ('（台湾纸）NxNcm单个;外径【单个价】长度Ncm', ('外径', '超硬')),
    ('宽x高）NxNcm外径台湾纸;长度Ncm', ('内径', '超硬')),
    ('宽x高）NxNcm;【外径】台湾纸】长度Ncm', ('内径', '超硬')),
    ('（宽x高）NxNcm外径台湾纸;长度Ncm', ('内径', '超硬')),
    ('（宽x高）NxNcm外径;长度Ncm【N个】', ('内径', '特硬')),
]:
    CONFIG[sk] = (dk, mat, p16_26)

# ===== 第7组: 宽度【N*N】cm =====
def p18_22(s):
    """宽度【N*N】cm【N个】;外径【xxx】长度Ncm"""
    l = grab_num(s, after='长度')
    wh = grab_two(s, after='宽度【')
    if not wh or not l: return None
    return (l, wh[0], wh[1])

for sk, mat in [
    ('宽度【N*N】cm【N个起拍】;外径【台湾纸】长度Ncm', '超硬'),
    ('宽度【N*N】cm【N个】;外径【双面白】长度Ncm', '白色'),
    ('宽度【N*N】cm;外径【N个】长度Ncm', '特硬'),
]:
    CONFIG[sk] = ('外径', mat, p18_22)

def p23(s):
    """【宽】NcmN个;外径【双面白】长度Ncm;高【Ncm】"""
    return p15(s)
CONFIG['【宽】NcmN个;外径【双面白】长度Ncm;高【Ncm】'] = ('外径', '白色', p23)

# ===== 第8组: mm系列 p27-29 =====
def p27_29(s):
    """（宽）Nmm外径;长度Nmm;Nmm台湾纸 等"""
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    vals = [float(n)/10 for n in nums[:3]]
    return (vals[1], vals[0], vals[2])

for sk, (dk, mat) in [
    ('（宽）Nmm外径;长度Nmm;Nmm台湾纸', ('内径', '超硬')),
    ('（宽）Nmm外径;【N个】长度Nmm;Nmm', ('内径', '特硬')),
    ('【宽N】mm单个价;长度【Nmm】;高【Nmm】外经', ('内径', '特硬')),
]:
    CONFIG[sk] = (dk, mat, p27_29)

# ===== 第9组: 宽x高）系列 p30-31 =====
def p30_31(s):
    wh = grab_two(s, after='宽x高）')
    if not wh: wh = grab_two(s, after='x高）')
    l = grab_num(s, after='长度')
    if not wh or not l: return None
    return (l, wh[0], wh[1])

for sk, (dk, mat) in [
    ('宽x高）NxNcm【N个】;【外径】双面白】长度Ncm', ('内径', '白色')),
    ('（双面白）NxNcm外径;【N个】长度Ncm', ('内径', '白色')),
]:
    CONFIG[sk] = (dk, mat, p30_31)

# ===== 第10组: mm系列 p32-34 =====
def p32_34(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    vals = [float(n)/10 for n in nums[:3]]
    return (vals[1], vals[0], vals[2])

for sk, (dk, mat) in [
    ('宽度【Nmm】台湾纸;长度【Nmm】;高度【Nmm】', ('内径', '超硬')),
    ('（宽）Nmm;长度Nmm【N个】;高Nmm外径', ('内径', '特硬')),
    ('宽度【Nmm】单个价;【N个起拍长度【Nmm】;高度【Nmm】', ('内径', '特硬')),
]:
    CONFIG[sk] = (dk, mat, p32_34)

CONFIG['台湾纸）NxNcm外径单价;长度Ncm'] = ('内径', '超硬', p16_26)

# ===== p36 =====
def p36(s):
    """【宽】Ncm外径;外径【N个】长度Ncm;高【Ncm】"""
    return (grab_num(s, after='长度'), grab_num(s, after='【宽】'), grab_num(s, after='高【'))
CONFIG['【宽】Ncm外径;外径【N个】长度Ncm;高【Ncm】'] = ('外径', '特硬', p36)

# ===== p37 =====
def p37(s):
    """（宽）Nmm;长度Nmm;高Nmm外径台湾纸"""
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[1])/10, float(nums[0])/10, float(nums[2])/10)
CONFIG['（宽）Nmm;长度Nmm;高Nmm外径台湾纸'] = ('内径', '超硬', p37)

# ===== p38-41 =====
def p38_41(s):
    """宽度【Nmm】...长度【Nmm】...;【Nmm】"""
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[1])/10, float(nums[0])/10, float(nums[2])/10)

for sk, mat in [
    ('宽度【Nmm】双面白;长度【Nmm】外径【N个】;【Nmm】', '白色'),
    ('宽度【Nmm】;长度【Nmm】外径【双面白】;【Nmm】【N个】', '白色'),
    ('宽度【Nmm】;长度【Nmm】外径【台湾纸】;【Nmm】单个', '超硬'),
    ('宽度【Nmm】台湾纸;长度【Nmm】外径【单个价】;【Nmm】【N个起拍', '超硬'),
]:
    CONFIG[sk] = ('外径', mat, p38_41)

# ===== p42 =====
def p42(s):
    """宽度【Nmm】N个;长度【Nmm】双面白;高度【Nmm】外尺寸"""
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[1])/10, float(nums[0])/10, float(nums[2])/10)
CONFIG['宽度【Nmm】N个;长度【Nmm】双面白;高度【Nmm】外尺寸'] = ('内径', '白色', p42)

# ===== p43-44 =====
def p43_44(s):
    wh = grab_two(s, after='宽x高）')
    if not wh: wh = grab_two(s, after='x高）')
    l = grab_num(s, after='长度')
    if not wh or not l: return None
    return (l, wh[0], wh[1])

for sk, (dk, mat) in [
    ('宽x高）NxNcm【N个】;【外径-双面白】长度Ncm', ('内径', '白色')),
    ('宽x高）NxNcm;【外径-台湾纸】长度Ncm', ('内径', '超硬')),
]:
    CONFIG[sk] = (dk, mat, p43_44)

# ===== p45 =====
CONFIG['宽度【Nmm】;长度【Nmm】【N个】;高度【Nmm】单个价'] = ('内径', '特硬', p42)

# ===== p46/p60/p108-109 宽度【N*N】cm =====
CONFIG['宽度【N*N】cm;外径【N个】长度Ncm'] = ('外径', '特硬', p18_22)
CONFIG['宽度【N*N】cm【;外径【N个】长度Ncm'] = ('外径', '特硬', p18_22)
CONFIG['宽度【N*N】cm】;外径【N个】长度Ncm'] = ('外径', '特硬', p18_22)
CONFIG['宽度【N*N】c;外径【N个】长度Ncm'] = ('外径', '特硬', p18_22)

# ===== p47 =====
def p47(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[0]), float(nums[1]), float(nums[2]))

CONFIG['牛皮色（可单卖）;（长宽cm）NXN;高Ncm'] = ('外径', '特硬', p47)

# ===== p48-49 E瓦 =====
def p48_49(s):
    wh = grab_two(s, after='【')
    h = grab_num(s, after='mm【高】') or grab_num(s, after='mm【高')
    if not wh or not h: return None
    return (wh[0]/10, wh[1]/10, h/10)

CONFIG['进口优质特硬E瓦-内径;长x宽【NxN】mm;Nmm【高】'] = ('内径', '特硬', p48_49)
CONFIG['进口优质特硬E瓦-外经;长x宽【NxN】mm;Nmm【高】'] = ('外径', '特硬', p48_49)

# ===== p50-55 加长/长方形盒 =====
def p50_55(s):
    l1 = grab_num(s, after='【长度】')
    wh = grab_two(s, after='宽高】')
    if not wh: wh = grab_two(s, after='【宽x高】')
    if not l1 or not wh: return None
    l2 = grab_num(s, after='加长')
    if l2:
        l_total = l1 + l2
    else:
        l_total = l1
    return (l_total, wh[0], wh[1])

for sk, (dk, mat) in [
    ('【长度】Ncm外径【双面白】;加长NCM】N个;宽高】NxNcm', ('外径', '白色')),
    ('【长度】Ncm外径【双面白】;加长Ncm】N个;宽高】NxNcm', ('外径', '白色')),
    ('【长度】Ncm外径【双面白】;长方形盒】N个;宽高】NxNcm', ('外径', '白色')),
    ('【长度】Ncm外径【N个】;加长NCM】;【宽x高】NxNcm', ('外径', '特硬')),
    ('【长度】Ncm外径【N个】;加长Ncm】;【宽x高】NxNcm', ('外径', '特硬')),
    ('【长度】Ncm外径【N个】;长方形盒;【宽x高】NxNcm', ('外径', '特硬')),
]:
    CONFIG[sk] = (dk, mat, p50_55)

# ===== p56 =====
def p56(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[1])/10, float(nums[0])/10, float(nums[2])/10)
CONFIG['宽度【Nmm;长度【Nmm】【N个】;高度【Nmm】单个价'] = ('内径', '特硬', p56)

# ===== p57-59 =====
def p57_59(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[0]), float(nums[1]), float(nums[2]))

for sk, (dk, mat) in [
    ('【超硬】台湾纸内径【即产品尺寸】;（长宽cm）NXN;高Ncm', ('内径', '超硬')),
    ('【超硬】台湾纸外径【即盒子尺寸】;（长宽cm）NXN;高Ncm', ('外径', '超硬')),
    ('新料钜惠【特硬外径】-便宜;（长宽cm）NXN;高Ncm', ('外径', '优质')),
]:
    CONFIG[sk] = (dk, mat, p57_59)

# ===== p61 纸箱EB =====
def p61(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[1]), float(nums[2]), float(nums[0]))

CONFIG['Ncm高【N个】;NxNcm;特硬N层加厚K=K'] = ('纸箱', None, p61)

# ===== p62-64 =====
def p62_64(s):
    wh = grab_two(s, after='【')
    h = grab_num(s, after=';【')
    if not h: h = grab_num(s, after='【NCM') or grab_num(s, after='NCM')
    if not wh or not h: return None
    return (wh[0], wh[1], h)

for sk, (dk, mat) in [
    ('【白色】内尺寸;长宽cm【N*N】;【NCM】', ('内径', '白色')),
    ('【白色】外尺寸;长宽cm【N*N】;【NCM】', ('外径', '白色')),
    ('新料钜惠【特硬内径】-黄色纸板;长宽cm【N*N】;【NCM】', ('内径', '优质')),
]:
    CONFIG[sk] = (dk, mat, p62_64)

# ===== p65 =====
def p65(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[1])/10, float(nums[0])/10, float(nums[2])/10)
CONFIG['宽度【Nmm】N个;长度【Nmm】双面白;高度【Nmm外尺寸】'] = ('内径', '白色', p65)

# ===== p66-68 =====
def p66_68(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[2]), float(nums[0]), float(nums[1]))

for sk, mat in [
    ('白色;NxNcm外径【N个】;Ncm', '白色'),
    ('黄色台湾纸超硬;NxNcm外径【N个】;Ncm', '超硬'),
    ('黄色特硬;NxNcm外径【N个】;Ncm', '特硬'),
]:
    CONFIG[sk] = ('外径', mat, p66_68)

# ===== p69-76 颜色系列 =====
def p69_76(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[0]), float(nums[1]), float(nums[2]))

for sk, (dk, mat) in [
    ('白色（至少要N个起卖哦）;（长宽cm）NXN;高Ncm', ('外径', '白色')),
    ('白色（至少要拍N个起哦）;（长宽cm）NXN;高Ncm', ('外径', '白色')),
    ('黑色（至少要拍N个起哦）;（长宽cm）NXN;高Ncm', ('外径', '黑色')),
    ('黑色（至少要N个起卖哦）;（长宽cm）NXN;高Ncm', ('外径', '黑色')),
]:
    CONFIG[sk] = (dk, mat, p69_76)

for sk in [
    '红色（至少要N个起卖哦）;（长宽cm）NXN;高Ncm',
    '蓝色（至少要N个起卖哦）;（长宽cm）NXN;高Ncm',
    '粉色（至少要拍N个起哦）;（长宽cm）NXN;高Ncm',
    '红色（至少要拍N个起哦）;（长宽cm）NXN;高Ncm',
    '粉色（至少要N个起拍哦）;（长宽cm）NxN;高Ncm【单个价】',
    '红色【至少N个起拍哦】;（长宽cm）NxN;高Ncm【单个价】',
    '蓝色【至少N个起拍哦】;（长宽cm）NxN;高Ncm【单个价】',
    '红色（至少要拍N个起哦）;（长宽cm）N*N;高Ncm',
    '粉色（至少要拍N个起哦）;（长宽cm）N*N;高Ncm',
    '蓝色（至少要拍N个起哦）;（长宽cm）N*N;高Ncm',
    '粉色（至少要N个起卖哦）;（长宽cm）N*N;高Ncm',
    '红色（至少要N个起卖哦）;（长宽cm）N*N;高Ncm',
    '蓝色（至少要N个起卖哦）;（长宽cm）N*N;高Ncm',
]:
    CONFIG[sk] = ('定制', None, None)

# ===== p77-82 =====
CONFIG['【双面白色】内径;【NxN】;Ncm高度（单个价）'] = ('内径', '白色', p69_76)
CONFIG['【双面白色】外径;【NxN】;Ncm高度（单个价）'] = ('外径', '白色', p69_76)
CONFIG['【台湾纸】内径;【NxN】;Ncm高度（单个价）'] = ('内径', '超硬', p69_76)
CONFIG['【台湾纸】外径;【NxN】;Ncm高度（单个价）'] = ('外径', '超硬', p69_76)
CONFIG['【特硬原色】内径;【NxN】;Ncm高度（单个价）'] = ('内径', '特硬', p69_76)
CONFIG['【特硬原色】外径;【NxN】;Ncm高度（单个价）'] = ('外径', '特硬', p69_76)

# ===== p83-89 =====
for sk, (dk, mat) in [
    ('牛皮色（巨硬台湾纸）;（长宽cm）NxN;高Ncm【单个价】', ('外径', '超硬')),
    ('牛皮色（玖龙S级）;（长宽cm）NxN;高Ncm【单个价】', ('外径', '特硬')),
    ('白色【至少N个起拍哦】;（长宽cm）NxN;高Ncm【单个价】', ('外径', '白色')),
    ('黑色【至少N个起拍哦】;（长宽cm）NxN;高Ncm【单个价】', ('外径', '黑色')),
    ('牛皮色（可单卖）;（长宽cm）N*N;高Ncm', ('外径', '特硬')),
    ('白色（至少要拍N个起哦）;（长宽cm）N*N;高Ncm', ('外径', '白色')),
    ('黑色（至少要拍N个起哦）;（长宽cm）N*N;高Ncm', ('外径', '黑色')),
]:
    CONFIG[sk] = (dk, mat, p69_76)

# ===== p90 =====
def p90(s):
    """【宽】Ncm外径;外径【N个】长度Ncm;高【Ncm"""
    return (grab_num(s, after='长度'), grab_num(s, after='【宽】'), grab_num(s, after='高【'))
CONFIG['【宽】Ncm外径;外径【N个】长度Ncm;高【Ncm'] = ('外径', '特硬', p90)

# ===== p91-93 定制 =====
for sk in [
    '宽度【Nmm】台湾纸;长度【Nmm】;内外长相差N宽高N',
    '意式N寸飞机盒：NxNcm;高Ncm（单个价）;黄色',
    '宽度【Nmm】单个价;【N个起拍长度【Nmm】;内外长相差N宽高N',
]:
    CONFIG[sk] = ('定制', None, None)

# ===== p94-96 =====
def p94_96(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[1])/10, float(nums[0])/10, float(nums[2])/10)

for sk, (dk, mat) in [
    ('（宽）Nmm;长宽Nmm;高Nmm外径台湾纸', ('内径', '超硬')),
    ('（宽）Nmm;长度Nmm.;高Nmm外径台湾纸', ('内径', '超硬')),
    ('（宽）Nmm;长宽Nmm【N个】;高Nmm外径', ('内径', '特硬')),
]:
    CONFIG[sk] = (dk, mat, p94_96)

# ===== p97 =====
CONFIG['【NXN】长宽【N;Ncm高【N个】'] = ('定制', None, None)

# ===== p98-99 =====
def p98_99(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[1])/10, float(nums[0])/10, float(nums[2])/10)

CONFIG['（宽）Nmm外径;长度Nmmm;Nmm台湾纸'] = ('内径', '超硬', p98_99)
CONFIG['（宽）Nmm外径;【N个】长度Nmmm;Nmm'] = ('内径', '特硬', p98_99)

# ===== p100-105 =====
def p100_105(s):
    wh = grab_two(s, after='x高）') or grab_two(s, after='（双面白）')
    if not wh: wh = grab_two(s, after='宽高）')
    if not wh: wh = grab_two(s, after='台湾纸）')
    if not wh: wh = grab_two(s, after='（宽x高）')
    if not wh: wh = grab_two(s, after='x高）')
    if not wh: wh = grab_two(s, after='宽x高）')
    if not wh: return None
    l = grab_num(s, after='长度')
    if l is None and wh:
        nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
        if len(nums) >= 3:
            l = max(float(nums[0]), float(nums[1]), float(nums[2]))
    if not wh or not l: return None
    return (l, wh[0], wh[1])

for sk, (dk, mat) in [
    ('宽x高）NxNcm【N个】;【外径】台湾纸】长度Ncm', ('内径', '超硬')),
    ('（双面白）NxNcm外经;【N个】长度Ncm', ('内径', '白色')),
    ('台湾纸）NxNcm外径单;长度Ncm', ('内径', '超硬')),
    ('台湾纸）NxNcm外经单价;长度Ncm', ('内径', '超硬')),
    ('宽x高）NxNcm外经;长度Ncm【N个】', ('内径', '特硬')),
    ('（宽x高）NxN;外径【N个】长度Ncm', ('外径', '特硬')),
]:
    CONFIG[sk] = (dk, mat, p100_105)

# ===== p106-107 定制 =====
CONFIG['进口优质特硬E瓦-内径;长x宽【NxN】mm;更硬牛皮-其他链接'] = ('定制', None, None)
CONFIG['进口优质特硬E瓦-外经;长x宽【NxN】mm;更硬牛皮-其他链接'] = ('定制', None, None)

# ===== p110-112 =====
def p110_112(s):
    wh = grab_two(s, after='【')
    h = grab_num(s, after=';【')
    if not h: h = grab_num(s, after='NCM')
    if not wh or not h: return None
    return (wh[0], wh[1], h)

for sk, (dk, mat) in [
    ('【白色】内尺寸;长宽cm【N*N】;【NCM', ('内径', '白色')),
    ('【白色】外尺寸;长宽cm【N*N】;【NCM', ('外径', '白色')),
    ('新料钜惠【特硬内径】-黄色纸板;长宽cm【N*N】;【NCM', ('内径', '优质')),
]:
    CONFIG[sk] = (dk, mat, p110_112)

# ===== p113-114 =====
CONFIG['【NXN】宽长【N;Ncm高【N个】'] = ('定制', None, None)
CONFIG['【纸盒【N层【Nmm厚【更多尺寸;Ncm高【N个】'] = ('定制', None, None)

# ===== p115/p155-156 =====
def p115_155_156(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[0])/10, float(nums[1])/10, float(nums[2])/10)

CONFIG['特硬【日本牛卡】外径;N-N-Nmm【N个】'] = ('外径', '特硬', p115_155_156)
CONFIG['特硬【日本牛卡】外径;N-*N*Nmm【N个】'] = ('外径', '特硬',
    lambda s: p115_155_156(s.replace('-*', '-')))
CONFIG['特硬【日本牛卡】外径;N-N*Nmm【N个】'] = ('外径', '特硬',
    lambda s: p115_155_156(s.replace('N*N', 'N-N').replace('*', '-')))

# ===== p121-126 T/B 系列 =====
def p121_126(s):
    nums = re.findall(r'(\d+(?:\.\d+)?)', s.replace(' ', ''))
    if len(nums) < 3: return None
    return (float(nums[0])/10, float(nums[1])/10, float(nums[2])/10)

for sk, mat in [
    ('三层E坑K纸（新材质）;TN(NmmxNmmxNmm)', '优质'),
    ('三层特硬;TN(NmmxNmmxNmm)', '特硬'),
    ('三层超硬;TN(NmmxNmmxNmm)', '超硬'),
    ('三层E坑K纸（新材质）;BN(NmmxNmmxNmm)', '优质'),
    ('三层特硬;BN(NmmxNmmxNmm)', '特硬'),
    ('三层超硬;BN(NmmxNmmxNmm)', '超硬'),
]:
    CONFIG[sk] = ('外径', mat, p121_126)

# ===== p142-150 AN/BN系列 =====
for sk, mat in [
    ('三层E坑K纸（新材质）;AN(Nmm*Nmm*Nmm)', '优质'),
    ('三层E坑K纸（新材质）;AN(NmmxNmmxNmm)', '优质'),
    ('三层E坑K纸（新材质）;BN(Nmm*Nmm*Nmm)', '优质'),
    ('三层特硬;AN(Nmm*Nmm*Nmm)', '特硬'),
    ('三层特硬;AN(NmmxNmmxNmm)', '特硬'),
    ('三层特硬;BN(Nmm*Nmm*Nmm)', '特硬'),
    ('三层超硬;AN(Nmm*Nmm*Nmm)', '超硬'),
    ('三层超硬;AN(NmmxNmmxNmm)', '超硬'),
    ('三层超硬;BN(Nmm*Nmm*Nmm)', '超硬'),
]:
    CONFIG[sk] = ('外径', mat, p121_126)

# ===== 所有定制 =====
CUSTOM_SKELS = [
    '按照价格截图客服拍下;下拉看详情选择尺寸',
    '定制类链接一但开始生产，不接受退货退款哈。要更硬材质，或者颜色，可咨询客服;N层;双插盒',
    '定制类链接一但开始生产，不接受退货退款哈。要更硬材质，或者颜色，可咨询客服;N层;扣抵盒',
    '飞机盒;定制产品不接受退货退款（拍下联系客服备注）',
    '材质厚度NMM三层;其他;双面白色',
    '材质厚度NMM三层;其他;特硬材质',
    '材质厚度NMM三层;其他;超硬材质',
    'N层E瓦厚度Nmm;其他;双面白色-N层E瓦',
    'N层E瓦厚度Nmm;其他;超硬台湾黄-N层E瓦',
    'N层E瓦楞NMM厚度;其他;外径飞机盒-台湾纸',
    'N层E瓦楞NMM厚度;其他;外径飞机盒-高档白色',
    '特硬【双面白色】N个组;更多尺寸-详情N款现模;其他省外【偏远除外】',
    '特硬【双面白色】N个组;更多尺寸-详情N款现模;广东省',
    '黄色【日本牛卡】N个组;更多尺寸-详情N款现模;其他省外【偏远除外】',
    '黄色【日本牛卡】N个组;更多尺寸-详情N款现模;广东省',
    '特硬-【双面白色N个】;下拉-详情页更多N款尺寸;其他省外【偏远除外】',
    '特硬-【双面白色N个】;下拉-详情页更多N款尺寸;广东省',
    '黄色-【日本牛卡N个】;下拉-详情页更多N款尺寸;其他省外【偏远除外】',
    '黄色-【日本牛卡N个】;下拉-详情页更多N款尺寸;广东省',
    'E瓦楞材质【外尺寸NMM厚】;其他;特硬黄色-N个',
    'E瓦楞材质【外尺寸NMM厚】;其他;超硬白-双面白-N个',
    'E瓦楞材质【外尺寸NMM厚】;其他;超硬黄-台湾纸-N个',
    '飞机盒订制（可订任意尺寸）',
    '材质厚度NMM三层;其他;特硬牛皮色',
    '材质厚度NMM三层;其他;超硬双面白色',
    'N层E瓦厚度NMM;其他;台湾黄超硬',
    'N层E瓦厚度NMM;其他;高档双面白色',
    '飞机盒-白色（N个）;更多尺寸-看详情;其他省外【偏远除外】',
    '飞机盒-白色（N个）;更多尺寸-看详情;广东省',
    '飞机盒-黄色（N个）;更多尺寸-看详情;其他省外【偏远除外】',
    '飞机盒-黄色（N个）;更多尺寸-看详情;广东省',
    '材质厚度NMM三层;其他;特硬黄色【外尺寸】',
    '材质厚度NMM三层;其他;超硬-双面白【外寸】',
    '材质厚度NMM三层;其他;超硬黄-台湾纸【外】',
    'N层E瓦NMM厚度外尺寸;其他;特硬【双面白色】',
    'N层E瓦NMM厚度外尺寸;其他;超硬【台湾纸】',
    'N层E瓦NMM厚度外尺寸;其他;黄色【日本牛卡】',
    '特硬【双面白色】N个组;更多尺寸看详情N个现模;其他省外【偏远除外】',
    '特硬【双面白色】N个组;更多尺寸看详情N个现模;广东省',
    '黄色【日本牛卡】N个组;更多尺寸看详情N个现模;其他省外【偏远除外】',
    '黄色【日本牛卡】N个组;更多尺寸看详情N个现模;广东省',
    '特硬【双面白色】N个;更多尺寸看详情列表;其他省外【偏远除外】',
    '特硬【双面白色】N个;更多尺寸看详情列表;广东省',
    '黄色【日本牛卡】飞机盒-N个;更多尺寸看详情列表;其他省外【偏远除外】',
    '黄色【日本牛卡】飞机盒-N个;更多尺寸看详情列表;广东省',
    '特硬【双面白色】外径N/组;更多【整数】尺寸-咨询客服;其他省外【偏远除外】',
    '特硬【双面白色】外径N/组;更多【整数】尺寸-咨询客服;广东省',
    '特硬黄色【日本牛卡】外径N/组;更多【整数】尺寸-咨询客服;其他省外【偏远除外】',
    '特硬黄色【日本牛卡】外径N/组;更多【整数】尺寸-咨询客服;广东省',
    '特硬【双面白色】外尺寸;详情-现模N个尺寸【下拉查看;其他省外【偏远除外】',
    '特硬【双面白色】外尺寸;详情-现模N个尺寸【下拉查看;广东省',
    '黄色【日本牛卡】外尺寸;详情-现模N个尺寸【下拉查看;其他省外【偏远除外】',
    '黄色【日本牛卡】外尺寸;详情-现模N个尺寸【下拉查看;广东省',
    '牛皮色k纸特硬;现货当天发',
]
for sk in CUSTOM_SKELS:
    CONFIG[sk] = ('定制', None, None)

print(f'已配置 {len(CONFIG)} 种结构模式')

# ===== 执行 =====
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

print(f'正常: {n_ok}, 纸箱EB: {n_zx}, 定制: {n_cus}, 失败(当定制): {n_fail}')
_write_excel(r'D:\Desktop\换绑_飞机盒品牌店.xlsx', codes)
print('DONE: 换绑_飞机盒品牌店.xlsx')
