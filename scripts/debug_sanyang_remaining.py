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

# 只找到底哪些结构还有问题
seen = {}
for idx in range(len(shop_data)):
    spec = str(shop_data.iloc[idx]['平台规格名称'] or '').strip()
    sk = make_skeleton(spec)
    seen[sk] = seen.get(sk, 0) + 1

# count how many rows in each failing structure
import openpyxl as oxl
wb = oxl.load_workbook(r'D:\Desktop\换绑_深圳市三羊包装材料有限公司.xlsx')
ws = wb.active
custom_codes = {}
for row in ws.iter_rows(min_row=3, values_only=True):
    code = str(row[3] or '')
    if code == '定制链接':
        sk = make_skeleton(str(row[2] or ''))
        custom_codes[sk] = custom_codes.get(sk, 0) + 1
wb.close()

print('所有标"定制链接"的结构:')
for sk, cnt in sorted(custom_codes.items(), key=lambda x: -x[1]):
    print(f'  [x{cnt}] {sk}')
