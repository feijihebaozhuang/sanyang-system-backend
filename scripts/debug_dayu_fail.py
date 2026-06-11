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

# 找所有配方但解析失败的结构
STRUCT_KEYS = [
    '长宽【NxNcm】；【N个】高【Ncm】黄色内径;长宽【NxNcm】;【N个】高【Ncm】黄色内径',
    '长宽【NxNcm】；【N个】高【Ncm】黄色外径;长宽【NxNcm】;【N个】高【Ncm】黄色外径',
    '【N个】高度【Ncm】黄色内径;长宽【NxNcm】',
    '长宽【NxNcm】；【N个】高度【Ncm】黄色外径;长宽【NxNcm】;【N个】高度【Ncm】黄色外径',
    '高度【Ncm】黄色外径;长宽【NxNcm】【N个】;高度【Ncm】黄色外径',
    '高度【Ncm】黄色内径N个;长宽【NxNcm】;高度【Ncm】黄色内径N个',
    '【N个】高度【Ncm】黄色外径;长宽【NxNcm】;【N个】高度【Ncm】黄色外径',
    '高度【Ncm特硬白色】;长宽【NxN】cm;高度【Ncm特硬白色】',
    '高度【Ncm特硬黄】;长宽【NxN】cm;高度【Ncm特硬黄】',
    '高度【Ncm超硬台湾纸】内径;长宽【NxN】cm;高度【Ncm超硬台湾纸】内径',
    '高度【Ncm超硬台湾纸】外径;长宽【NxN】cm;高度【Ncm超硬台湾纸】外径',
    '高度【Ncm特硬白色】内径;长宽【NxN】cm内径尺寸;高度【Ncm特硬白色】内径',
    '高度【Ncm特硬黄】内径;长宽【NxN】cm内径尺寸;高度【Ncm特硬黄】内径',
    '高度【Ncm】黄色外径【N个】;长宽【NxNcm】;高度【Ncm】黄色外径【N个】',
    'N个长宽N*N；高N【N层】;N个长宽N*N;高N【N层】',
    '高【Ncm】黄色内径;长宽【NxNcm】N个',
    '高度【Ncm】黄色外径;长宽【NxNcm】N个',
    '高度【Ncm】黄色外径N个*长宽【NxNcm】;长宽【NxNcm】;高度【Ncm】黄色外径N个',
    '长宽【NxNcm】；高【Ncm】黄色内径【N个】;长宽【NxNcm】;高【Ncm】黄色内径【N个】',
    '长宽【NxNcm】；高【Ncm】黄色外径【N个】;长宽【NxNcm】;高【Ncm】黄色外径【N个】',
    '长Ncm【N个】；宽-高【N*Ncm】外径;长Ncm【N个】;宽-高【N*Ncm】外径',
    '长宽【NxN】cm；高度【Ncm】；黑色N个一组;长宽【NxN】cm;高度【Ncm】;黑色N个一组',
    '长宽【NxNcm】；高度【Ncm】【内径N个】;长宽【NxNcm】;高度【Ncm】【内径N个】',
    '高度【Ncm超硬白色】内径;长宽【NxN】cm',
    '高度【Ncm超硬白色】外径;长宽【NxN】cm',
    '长宽【NxNcm】；【N个】高度【Ncm】黄色内径;长宽【NxNcm】;【N个】高度【Ncm】黄色内径',
    '长宽【NxNcm】；高度【Ncm】黄色内径【N个】;长宽【NxNcm】;高度【Ncm】黄色内径【N个】',
    '长宽【NxNcm】；高度【Ncm】黄色外径N个;长宽【NxNcm】;高度【Ncm】黄色外径N个',
    '高度【Ncm】黄色内径N个*长宽【NxNcm】;长宽【NxNcm】;高度【Ncm】黄色内径N个',
    '长宽【NxNcm】；高度【Ncm】【外径N个】;长宽【NxNcm】;高度【Ncm】【外径N个】',
    '长宽【NxNm】；【N个】高【Ncm】黄色外径;长宽【NxNm】;【N个】高【Ncm】黄色外径',
    '长宽【NxNm】；【N个】高【Ncm】黄色内径;长宽【NxNm】;【N个】高【Ncm】黄色内径',
    '高度【Ncm】黄色内径*长宽【NxNcm】;长宽【NxNcm】;高度【Ncm】黄色内径',
    '长宽【NxNm】；高度【Ncm】黄色外径N个;长宽【NxNm】;高度【Ncm】黄色外径N个',
    '高度【Ncm】黄色内径N个;长宽【NxNm】;高度【Ncm】黄色内径N个',
    '高度【Ncm】黄色外径;长宽【NxNm】【N个】;高度【Ncm】黄色外径',
    '长宽【NxNm】；高度【Ncm】【内径N个】;长宽【NxNm】;高度【Ncm】【内径N个】',
    '高度【Ncm】黄色外径;长宽【NxNcm】【N个】】;高度【Ncm】黄色外径',
    '高度【Ncm特硬白色】内径;长宽【NxN】cm;高度【Ncm特硬白色】内径',
    '高度【Ncm特硬黄】内径;长宽【NxN】cm;高度【Ncm特硬黄】内径',
]

# 统计每个骨架有多少行，以及是否有行没匹配到配置
sk_found = defaultdict(int)
sk_not_in_config = defaultdict(list)

for idx in range(len(shop_data)):
    spec = str(shop_data.iloc[idx]['平台规格名称'] or '').strip()
    sk = make_skeleton(spec)
    if sk not in STRUCT_KEYS:
        if sk not in sk_not_in_config:
            sk_not_in_config[sk] = []
        sk_not_in_config[sk].append(spec)
    else:
        sk_found[sk] += 1

# 检查不在配方中的结构
if sk_not_in_config:
    print(f'⚠️ 有 {len(sk_not_in_config)} 个骨架不在配置中:')
    for sk, specs in sorted(sk_not_in_config.items(), key=lambda x: -len(x[1])):
        print(f'  行数: {len(specs)}, 骨架: {sk}')
        print(f'    样例: {specs[0][:100]}')
        print()

# 检查配方中但0行的
for sk in STRUCT_KEYS:
    if sk_found.get(sk, 0) == 0:
        print(f'⚠️ 配方存在但无数据: {sk}')
        print()
