# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import openpyxl as oxl

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
shop_name = '深圳市三羊包装材料有限公司'

df = pd.read_excel(source, dtype=str)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']
sd = data[data['店铺名称'].str.strip() == shop_name].copy()

# 分析失败的结构
wb = oxl.load_workbook(r'D:\Desktop\换绑_深圳市三羊包装材料有限公司.xlsx')
ws = wb.active
from collections import Counter

fail_specs = []
for idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True)):
    code = str(row[3] or '')
    if code == '定制链接':
        spec = str(sd.iloc[idx]['平台规格名称'] or '').strip()
        fail_specs.append(spec)

# 找前10个失败样例
for spec in fail_specs[:10]:
    print(f'  规格: {spec[:120]}')
print(f'总失败: {len(fail_specs)}')
